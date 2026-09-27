"""Step 4 (v2) — FFmpeg se complete edit.

  * Ratio: 16:9 (1920x1080), 9:16 (1080x1920), 1:1 (1080x1080)
  * Har 4s clip par Ken Burns animation (zoom in/out, pan — automatic, rotate hoti hai)
  * Clips ke darmiyan 0.5s crossfade transitions (automatic)
  * Background music (user upload ya auto ambient pad) + har transition par whoosh SFX
  * Smart volume: music voice ke neeche auto-duck (sidechain compression)
  * remix_audio(): sirf audio dobara mix karta hai — video re-encode nahi,
    is liye volume sliders foran apply hote hain.
"""

import json
import os
import subprocess

RATIOS = {
    "16:9": (1920, 1080, "landscape"),
    "9:16": (1080, 1920, "portrait"),
    "1:1": (1080, 1080, "square"),
}
CHUNK = 4.0      # har visual max 4 second
XFADE = 0.5      # transition duration
FPS = 30


def _run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError("FFmpeg error:\n" + (p.stderr or "")[-2000:])
    return p


def probe_duration(path):
    p = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True)
    return float(p.stdout.strip())


def make_placeholder(duration, out_path, w, h):
    _run(["ffmpeg", "-y", "-f", "lavfi",
          "-i", f"testsrc2=size={w}x{h}:rate={FPS}:duration={duration:.2f}",
          "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
          "-pix_fmt", "yuv420p", "-an", out_path])
    return out_path


def kenburns_vf(w, h, duration, variant):
    """Automatic animation: 0=zoom in, 1=zoom out, 2=pan right, 3=pan left."""
    frames = max(1, int(duration * FPS))
    sw, sh = int(w * 1.3), int(h * 1.3)
    cx, cy = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    if variant == 0:
        z, x, y = f"1+0.25*in/{frames}", cx, cy
    elif variant == 1:
        z, x, y = f"1.25-0.25*in/{frames}", cx, cy
    elif variant == 2:
        z, x, y = "1.25", f"(iw-iw/zoom)*in/{frames}", cy
    else:
        z, x, y = "1.25", f"(iw-iw/zoom)*(1-in/{frames})", cy
    return (
        f"scale={sw}:{sh}:force_original_aspect_ratio=increase,"
        f"crop={sw}:{sh},setsar=1,fps={FPS},"
        f"zoompan=z='{z}':x='{x}':y='{y}':d=1:s={w}x{h}:fps={FPS}"
    )


def build_segment(src, duration, out_path, w, h, variant):
    _run(["ffmpeg", "-y",
          "-stream_loop", "-1", "-i", src,
          "-vf", kenburns_vf(w, h, duration, variant),
          "-t", f"{duration:.2f}",
          "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
          "-pix_fmt", "yuv420p", "-an", out_path])
    return out_path


def xfade_concat(seg_paths, durations, out_path, xf=XFADE):
    n = len(seg_paths)
    if n == 1:
        _run(["ffmpeg", "-y", "-i", seg_paths[0], "-c", "copy", out_path])
        return out_path
    cmd = ["ffmpeg", "-y"]
    for p in seg_paths:
        cmd += ["-i", p]
    parts = []
    off = durations[0] - xf
    parts.append(f"[0:v][1:v]xfade=transition=fade:duration={xf}:offset={off:.3f}[x1]")
    for i in range(2, n):
        off = off + durations[i - 1] - xf
        parts.append(
            f"[x{i-1}][{i}:v]xfade=transition=fade:duration={xf}:offset={off:.3f}[x{i}]")
    cmd += ["-filter_complex", ";".join(parts),
            "-map", f"[x{n-1}]",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-an", out_path]
    _run(cmd)
    return out_path


# ---------------- Audio: music + sfx + smart volume ----------------

def make_ambient_music(duration, out_path):
    """Royalty-free ambient pad (procedural) — A-major drone."""
    expr = ("0.22*sin(2*PI*110*t)+0.18*sin(2*PI*164.81*t)"
            "+0.14*sin(2*PI*220*t)+0.10*sin(2*PI*277.18*t)")
    _run(["ffmpeg", "-y", "-f", "lavfi",
          "-i", f"aevalsrc='{expr}':s=44100:d={duration:.2f}",
          "-af", "aformat=channel_layouts=stereo,tremolo=f=0.12:d=0.7,"
                 "lowpass=f=900,volume=0.6",
          "-c:a", "aac", "-b:a", "128k", out_path])
    return out_path


def make_silence(duration, out_path):
    _run(["ffmpeg", "-y", "-f", "lavfi",
          "-i", f"anullsrc=r=44100:cl=stereo:d={duration:.2f}",
          "-c:a", "aac", out_path])
    return out_path


def make_whoosh(out_path):
    """0.7s upward sweep — transition SFX."""
    expr = "sin(2*PI*(250+1400*t/0.7)*t)*sin(PI*t/0.7)"
    _run(["ffmpeg", "-y", "-f", "lavfi",
          "-i", f"aevalsrc='{expr}':s=44100:d=0.7",
          "-af", "aformat=channel_layouts=stereo,volume=0.8",
          "-c:a", "aac", out_path])
    return out_path


def build_sfx_bed(transition_times, whoosh_path, out_path, duration):
    """Har transition par whoosh (0.25s pehle). Koi transition na ho to silence."""
    if not transition_times:
        return make_silence(duration, out_path)
    cmd = ["ffmpeg", "-y"]
    for _ in transition_times:
        cmd += ["-i", whoosh_path]
    parts = []
    for i, tt in enumerate(transition_times):
        ms = int(max(0.0, tt - 0.25) * 1000)
        parts.append(f"[{i}:a]adelay={ms}|{ms}[s{i}]")
    labels = "".join(f"[s{i}]" for i in range(len(transition_times)))
    parts.append(f"{labels}amix=inputs={len(transition_times)}:duration=longest:normalize=0[sfx]")
    cmd += ["-filter_complex", ";".join(parts),
            "-map", "[sfx]", "-t", f"{duration:.2f}",
            "-c:a", "aac", out_path]
    _run(cmd)
    return out_path


def convert_audio(src, out_path, duration):
    _run(["ffmpeg", "-y", "-i", src,
          "-ar", "44100", "-ac", "2", "-t", f"{duration:.2f}",
          "-c:a", "aac", "-b:a", "128k", out_path])
    return out_path


def mix_final(video_silent, voice_path, music_path, sfx_bed, out_path,
              duration, music_vol=0.25, sfx_vol=0.35):
    """Voice full volume; music auto-duck (voice ke neeche dabti hai); sfx mix.

    music_vol / sfx_vol 0.0-1.0 — preview ke sliders se aate hain.
    """
    fc = (
        f"[2:a]volume={music_vol}[mus];"
        f"[3:a]volume={sfx_vol}[sfx];"
        f"[mus][1:a]sidechaincompress=threshold=0.03:ratio=8:"
        f"attack=20:release=400[duck];"
        f"[1:a][duck][sfx]amix=inputs=3:duration=first:normalize=0[aout]"
    )
    _run(["ffmpeg", "-y",
          "-i", video_silent,
          "-i", voice_path,
          "-stream_loop", "-1", "-i", music_path,
          "-i", sfx_bed,
          "-filter_complex", fc,
          "-map", "0:v", "-map", "[aout]",
          "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
          "-t", f"{duration:.2f}",
          "-movflags", "+faststart", out_path])
    return out_path


def remix_audio(work_dir, music_vol, sfx_vol, out_name="final.mp4"):
    """Sirf audio dobara mix karo (video copy) — sliders foran apply hon."""
    meta_path = os.path.join(work_dir, "meta.json")
    with open(meta_path) as f:
        meta = json.load(f)
    out_path = os.path.join(work_dir, out_name)
    mix_final(meta["video_silent"], meta["voice_src"], meta["music_src"],
              meta["sfx_bed"], out_path, meta["duration"],
              music_vol=music_vol, sfx_vol=sfx_vol)
    return out_path
