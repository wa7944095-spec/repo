#!/usr/bin/env python3
"""VoiceCut Studio v2 — command line.

Usage:
    python run.py voice.mp3 --ratio 9:16 --out final.mp4
    python run.py voice.mp3 --ratio 16:9 --music bgm.mp3 --out final.mp4

API keys .env se load hoti hain (PEXELS_API_KEY, PIXABAY_API_KEY).
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pipeline.config import load_keys  # noqa: E402
from pipeline.run_pipeline import run_pipeline  # noqa: E402
from pipeline.assemble import RATIOS  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="Voice-over se auto-edited video banao")
    ap.add_argument("audio", help="Voice-over file (mp3/wav/m4a)")
    ap.add_argument("--ratio", default="16:9", choices=list(RATIOS.keys()))
    ap.add_argument("--music", default=None, help="Background music file (optional)")
    ap.add_argument("--no-auto-music", action="store_true")
    ap.add_argument("--no-sfx", action="store_true")
    ap.add_argument("--music-vol", type=float, default=0.25)
    ap.add_argument("--sfx-vol", type=float, default=0.35)
    ap.add_argument("--out", default="final.mp4")
    args = ap.parse_args()

    result = run_pipeline(
        args.audio, os.path.join(os.path.dirname(os.path.abspath(args.out)),
                                 ".voicecut_work"),
        ratio=args.ratio, keys=load_keys(),
        music_path=args.music, auto_music=not args.no_auto_music,
        sfx_on=not args.no_sfx,
        music_vol=args.music_vol, sfx_vol=args.sfx_vol,
        progress=lambda t, f: print(f"[{int(f*100):3d}%] {t}", flush=True),
    )
    os.replace(result["final"], os.path.abspath(args.out))
    print(f"\n✅ Video tayyar: {os.path.abspath(args.out)}")
    print(f"   Ratio: {result['ratio']} | Clips: {result['chunks']} | "
          f"Duration: {result['duration']:.1f}s | Music: {result['music']}")
    for s in result["scenes"]:
        print(f"   - Clip {s['clip']} [{s['start']}s] '{s['query']}' -> {s['visual']}")


if __name__ == "__main__":
    main()
