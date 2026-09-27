# 🎬 VoiceCut Studio

Voice-over upload karo → tool khud visuals dhoondhega → voice ki timing par edit karega → downloadable MP4 dega.

## Flow

```
Upload Voice-over
       ↓
AI audio analyze (speech-to-text, faster-whisper — local & free)
       ↓
Scenes/segments mein divide (timing ke saath)
       ↓
Har scene ka meaning → search query (keyword extractor)
       ↓
Pexels se relevant HD clips (free, legal stock footage)
       ↓
Voice-over timing ke mutabiq arrange
       ↓
FFmpeg se edit + voice mix
       ↓
Downloadable MP4 ✅
```

## Setup (5 minute)

```bash
cd voicecut
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

System mein **FFmpeg** hona chahiye (`ffmpeg -version` se check karo).

## Pexels API key (free, 2 minute)

1. https://www.pexels.com/api/ par free account banao
2. API key copy karo
3. App mein paste karo (ya `PEXELS_API_KEY` env var set karo)

Key ke baghair bhi pipeline chalti hai — bas asli footage ki jagah
placeholder visuals lagte hain (testing ke liye).

## Chalao

**Web app:**
```bash
streamlit run app.py
```

**Command line:**
```bash
python run.py voice.mp3 --pexels-key TUMHARI_KEY --out final.mp4
```

## Visual sources (4 — automatic chain)

Har 4-second clip ke liye tool ye order try karta hai (pehla kamyab source use hota hai):

1. **YouTube** — pehli preference, koi bhi video (license filter nahi)
2. **Pexels** — key `.env` mein set hai ✅
3. **Pixabay** — key `.env` mein set hai ✅
4. **Coverr** — key `.env` mein set hai ✅ ("AI Video Editor" app)

Koi source na mile to placeholder visual lagta hai — pipeline kabhi nahi rukti.

> Note: YouTube se non-CC videos uthane par jab final video apne channel par
> upload karoge to Content ID claim ya copyright strike ka risk hota hai.

## Features (v2)

- 📐 Ratio select: 16:9 / 9:16 / 1:1
- 🎬 Har visual max 4 second; video duration = voice-over duration (exact)
- ✨ Automatic 0.5s crossfade transitions + Ken Burns animation (zoom/pan rotate)
- 🎵 Background music (upload ya auto ambient) + transition whoosh SFX
- 🔊 Smart volume: music voice ke neeche auto-duck; preview mein sliders se adjust
- ⬇️ HD MP4 download
