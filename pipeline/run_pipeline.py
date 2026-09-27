"""Orchestrator (v2).

  voice.mp3 (D seconds)
      -> transcribe -> scenes
      -> D/4 chunks (har chunk max 4s) — chunk ka query us waqt ke scene se
      -> har chunk: YouTube/Pexels/Pixabay/Coverr se clip (ya placeholder)
      -> Ken Burns animation + 0.5s crossfade transitions (FFmpeg)
      -> music (upload ya auto ambient) + whoosh SFX + auto-ducking
      -> final.mp4 — bilkul D seconds, HD, downloadable

  Duration guarantee: har chunk 4.5s (aakhri chunk apni asal length),
  xfade 0.5s overlap kha jata hai -> total = D exactly.
"""

import math
import os

from .transcribe import transcribe
from .keywords import extract_query
from .footage import fetch_visual
from .assemble import (
    RATIOS, CHUNK, XFADE, probe_duration, make_placeholder, build_segment,
    xfade_concat, make_ambient_music, make_silence, make_whoosh,
    build_sfx_bed, convert_audio, mix_final,
)
import json as _json


def run_pipeline(audio_path, work_dir, ratio="16:9", keys=None,
                 music_path=None, auto_music=True, sfx_on=True,
                 music_vol=0.25, sfx_vol=0.35, progress=None):
    keys = keys or {}
    W, H, orientation = RATIOS.get(ratio, RATIOS["16:9"])
    os.makedirs(work_dir, exist_ok=True)
    clips_dir = os.path.join(work_dir, "clips")
    segs_dir = os.path.join(work_dir, "segments")
    os.makedirs(clips_dir, exist_ok=True)
    os.makedirs(segs_dir, exist_ok=True)

    def _p(text, frac):
        if progress:
            progress(text, frac)

    _p("🎧 Voice-over analyze ho rahi hai...", 0.03)
    D = probe_duration(audio_path)

    # voice copy (remix ke liye)
    voice_src = os.path.join(work_dir, "voice_src.m4a")
    convert_audio(audio_path, voice_src, D)

    t = transcribe(audio_path, min_scene_secs=4.0, max_scene_secs=16.0)
    scenes = t["scenes"]

    # ---- 4-second chunks ----
    N = max(1, int(math.ceil(D / CHUNK)))
    chunks = []
    for i in range(N):
        s = i * CHUNK
        d = min(CHUNK, D - s)
        chunks.append((s, d))

    def query_for(mid):
        for sc in scenes:
            if sc["start"] <= mid < sc["end"]:
                return extract_query(sc["text"]), sc["text"]
        if scenes:
            return extract_query(scenes[-1]["text"]), scenes[-1]["text"]
        return "cinematic b-roll", ""

    report, seg_paths, seg_durs = [], [], []
    for i, (s, d) in enumerate(chunks):
        mid = s + d / 2
        query, stext = query_for(mid)
        _p(f"🎬 Clip {i+1}/{N}: '{query}'", 0.05 + 0.55 * i / N)

        dest = os.path.join(clips_dir, f"chunk{i+1:03d}.mp4")
        found = fetch_visual(query, dest, keys, orientation)
        if found:
            src, vsource, credit = found["path"], found["source"], found["credit"]
        else:
            make_placeholder(d + (XFADE if i < N - 1 else 0), dest, W, H)
            src, vsource, credit = dest, "placeholder", "-"

        seg_dur = d + (XFADE if i < N - 1 else 0.0)
        seg_path = os.path.join(segs_dir, f"seg{i+1:03d}.mp4")
        build_segment(src, seg_dur, seg_path, W, H, variant=i % 4)
        seg_paths.append(seg_path)
        seg_durs.append(seg_dur)
        report.append({"clip": i + 1, "start": round(s, 1),
                       "duration": round(d, 1), "query": query,
                       "visual": vsource, "credit": credit,
                       "text": stext[:100]})

    _p("✨ Transitions + animation lag rahi hai...", 0.65)
    video_silent = os.path.join(work_dir, "video_silent.mp4")
    xfade_concat(seg_paths, seg_durs, video_silent)

    _p("🎵 Music aur sound effects...", 0.78)
    if music_path and os.path.isfile(music_path):
        music_src = os.path.join(work_dir, "music_src.m4a")
        convert_audio(music_path, music_src, D)
        music_note = "uploaded"
    elif auto_music:
        music_src = os.path.join(work_dir, "music_auto.m4a")
        make_ambient_music(D, music_src)
        music_note = "auto ambient"
    else:
        music_src = os.path.join(work_dir, "music_silence.m4a")
        make_silence(D, music_src)
        music_note = "off"

    whoosh = os.path.join(work_dir, "whoosh.m4a")
    make_whoosh(whoosh)
    trans_times = [(i + 1) * CHUNK for i in range(N - 1)] if sfx_on else []
    sfx_bed = os.path.join(work_dir, "sfx_bed.m4a")
    build_sfx_bed(trans_times, whoosh, sfx_bed, D)

    with open(os.path.join(work_dir, "meta.json"), "w") as f:
        _json.dump({"duration": D, "ratio": ratio, "chunks": N,
                    "video_silent": video_silent, "voice_src": voice_src,
                    "music_src": music_src, "sfx_bed": sfx_bed}, f)

    _p("🔊 Final mix (smart volume)...", 0.9)
    final = os.path.join(work_dir, "final.mp4")
    mix_final(video_silent, voice_src, music_src, sfx_bed, final, D,
              music_vol=music_vol, sfx_vol=sfx_vol)

    _p("✅ Tayyar!", 1.0)
    return {"final": final, "work_dir": work_dir, "scenes": report,
            "duration": D, "ratio": ratio, "chunks": N,
            "music": music_note, "language": t["language"]}
