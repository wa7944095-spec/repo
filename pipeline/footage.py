"""Step 3 (v2) — Har 4-second chunk ke liye relevant visual clip.


Source chain — pehla kamyab source use hota hai:
  1. YouTube (koi bhi video — license filter nahi; pehli preference)
  2. Pexels  (free stock, API key .env mein)
  3. Pixabay (free stock, API key .env mein)
  4. Coverr  (free stock, API key .env mein)
  5. Placeholder (koi source na mile to — pipeline kabhi nahi rukti)


Note: YouTube kabhi kabhi datacenter IPs ko 429 (rate limit) deta hai;
us waqt chain automatically agle source par chali jati hai.
"""


import json
import os
import subprocess
import sys
import time


import requests


TIMEOUT = 25


# YouTube ne is run mein rate-limit kar diya to baqi clips ke liye
# waqt zaya kiye baghair seedha agle source par jao.
_YT_THROTTLED = False


def valid_clip(dest, min_secs=2.0):
    """Downloaded clip waqayi chalti hui video hai ya khokhli/corrupt file?"""
    try:
        if not os.path.isfile(dest) or os.path.getsize(dest) < 50000:
            return False
        p = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=codec_type:format=duration",
             "-of", "default=noprint_wrappers=1", dest],
            capture_output=True, text=True, timeout=30)
        out = p.stdout or ""
        if "codec_type=video" not in out:
            return False
        for line in out.splitlines():
            if line.startswith("duration="):
                try:
                    if float(line.split("=", 1)[1]) < min_secs:
                        return False
                except ValueError:
                    pass
        return True
    except Exception:
        return False


def _remove_bad(dest):
    try:
        if os.path.isfile(dest):
            os.remove(dest)
    except OSError:
        pass


def _download(url, dest, min_bytes=50000, timeout=120):
    try:
        r = requests.get(url, timeout=timeout)
        if r.status_code == 200 and len(r.content) > min_bytes:
            with open(dest, "wb") as f:
                f.write(r.content)
            if valid_clip(dest):
                return True
            _remove_bad(dest)  # corrupt download — reject
    except Exception:
        pass
    return False




def pexels_clip(query, api_key, dest, orientation="landscape"):
    if not api_key:
        return None
    try:
        r = requests.get(
            "https://api.pexels.com/videos/search",
            headers={"Authorization": api_key},
            params={"query": query, "per_page": 5,
                    "orientation": orientation, "size": "medium"},
            timeout=TIMEOUT)
        if r.status_code != 200:
            return None
        for v in r.json().get("videos", []):
            files = sorted(v.get("video_files", []),
                           key=lambda f: f.get("width", 0), reverse=True)
            mp4s = [f for f in files
                    if f.get("file_type") == "video/mp4"
                    and f.get("width", 0) >= 640]
            if not mp4s:
                continue
            if _download(mp4s[0]["link"], dest):
                return {"path": dest, "source": "pexels",
                        "credit": v.get("user", {}).get("name", "Pexels")}
    except Exception:
        pass
    return None




def pixabay_clip(query, api_key, dest):
    if not api_key:
        return None
    try:
        r = requests.get(
            "https://pixabay.com/api/videos/",
            params={"key": api_key, "q": query, "per_page": 3,
                    "safesearch": "true"},
            timeout=TIMEOUT)
        if r.status_code != 200:
            return None
        for h in r.json().get("hits", []):
            vids = h.get("videos", {})
            for size in ("medium", "large", "small"):
                url = vids.get(size, {}).get("url")
                if url and _download(url, dest):
                    return {"path": dest, "source": "pixabay",
                            "credit": str(h.get("user", "Pixabay"))}
    except Exception:
        pass
    return None




def coverr_clip(query, api_key, dest, vertical=False):
    """Coverr.co free stock — API key lazmi (free: coverr.co/developers)."""
    if not api_key:
        return None
    try:
        r = requests.get(
            "https://api.coverr.co/videos",
            headers={"Authorization": f"Bearer {api_key}"},
            params={"query": query, "urls": "true", "page_size": 5},
            timeout=TIMEOUT)
        if r.status_code != 200:
            return None
        hits = r.json().get("hits", [])


        def pick(want_vertical):
            for h in hits:
                is_v = bool(h.get("is_vertical"))
                if want_vertical is not None and is_v != want_vertical:
                    continue
                urls = h.get("urls") or {}
                url = urls.get("mp4_download") or urls.get("mp4")
                if url and _download(url, dest):
                    title = (h.get("title") or "Coverr")[:40]
                    return {"path": dest, "source": "coverr",
                            "credit": title}
            return None


        # pehle ratio ke mutabiq orientation, phir koi bhi
        return pick(vertical) or pick(None)
    except Exception:
        pass
    return None




def youtube_clip(query, dest):
    """YouTube se clip — koi bhi video (license filter nahi). Pehli preference.
    Pehle 3 results try karta hai (koi ek fail ho to agla)."""
    global _YT_THROTTLED
    if _YT_THROTTLED:
        return None
    try:
        cmd = [sys.executable, "-m", "yt_dlp", "-J", "--no-check-certificate",
               "--default-search", "ytsearch",
               "--no-playlist", "--socket-timeout", "20",
               f"ytsearch6:{query}"]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        if p.returncode != 0:
            return None
        entries = [e for e in (json.loads(p.stdout).get("entries") or [])
                   if e and e.get("webpage_url")][:3]
        if not entries:
            return None
        saw_429 = False
        for i, chosen in enumerate(entries):
            if i:
                time.sleep(2)
            try:
                url = chosen["webpage_url"]
                credit = chosen.get("uploader") or chosen.get("channel") or "YouTube"
                g = subprocess.run(
                    [sys.executable, "-m", "yt_dlp", "-g", "--no-check-certificate",
                     "--extractor-args", "youtube:player_client=android",
                     "-f", "bv[height<=1080][ext=mp4]+ba[ext=m4a]/b[ext=mp4]/b",
                     "--no-playlist", "--socket-timeout", "20", url],
                    capture_output=True, text=True, timeout=90)
                if g.returncode != 0 or not g.stdout.strip():
                    if "429" in g.stderr or "not a bot" in g.stderr:
                        saw_429 = True
                    continue
                stream = g.stdout.strip().split("\n")[0]
                f = subprocess.run(
                    ["ffmpeg", "-y", "-ss", "8", "-i", stream,
                     "-t", "4.5", "-c:v", "libx264", "-preset", "veryfast",
                     "-crf", "21", "-pix_fmt", "yuv420p", "-an", dest],
                    capture_output=True, text=True, timeout=180)
                if f.returncode == 0 and valid_clip(dest):
                    return {"path": dest, "source": "youtube",
                            "credit": str(credit)[:40]}
                _remove_bad(dest)  # tooti/corrupt download — agla result try karo
            except Exception:
                continue
        if saw_429:
            _YT_THROTTLED = True
    except Exception:
        pass
    return None




def fetch_visual(query, dest, keys, orientation="landscape"):
    """Chain try karo: YouTube -> Pexels -> Pixabay -> Coverr.
    Dict {path, source, credit} ya None (phir placeholder)."""
    keys = keys or {}
    result = youtube_clip(query, dest)
    if result:
        return result
    result = pexels_clip(query, keys.get("pexels"), dest, orientation)
    if result:
        return result
    result = pixabay_clip(query, keys.get("pixabay"), dest)
    if result:
        return result
    result = coverr_clip(query, keys.get("coverr"), dest,
                         vertical=(orientation == "portrait"))
    if result:
        return result
    return None
