"""VoiceCut Studio v2 — web app.

    streamlit run app.py
"""

import os
import shutil
import tempfile

import streamlit as st

from pipeline.config import load_keys
from pipeline.run_pipeline import run_pipeline
from pipeline.assemble import remix_audio, RATIOS

st.set_page_config(page_title="VoiceCut Studio", page_icon="🎬", layout="centered")
st.title("🎬 VoiceCut Studio")
st.write("Voice-over upload karo — tool khud 4-second visuals, transitions, "
         "animation, music aur sound effects lagayega. Phir preview mein "
         "volume adjust karo aur HD video download karo.")

keys = load_keys()

# ---------- inputs ----------
audio = st.file_uploader("🎤 Voice-over (MP3 / WAV / M4A)", type=["mp3", "wav", "m4a", "ogg"])

ratio = st.radio("📐 Video ratio", list(RATIOS.keys()), horizontal=True,
                 format_func=lambda r: {"16:9": "16:9 — YouTube",
                                        "9:16": "9:16 — Reels / Shorts",
                                        "1:1": "1:1 — Post"}[r])

col1, col2 = st.columns(2)
with col1:
    music_up = st.file_uploader("🎵 Background music (optional)", type=["mp3", "wav", "m4a"])
with col2:
    auto_music = st.checkbox("Auto ambient music", value=True,
                             help="Apni music na ho to tool khud halki ambient music banayega.")
sfx_on = st.checkbox("✨ Transition sound effects", value=True)

with st.expander("🔑 API keys"):
    st.write(f"Pexels: {'✅ set' if keys.get('pexels') else '❌ missing'} &nbsp;&nbsp; "
             f"Pixabay: {'✅ set' if keys.get('pixabay') else '❌ missing'} &nbsp;&nbsp; "
             f"Coverr: {'✅ set' if keys.get('coverr') else '❌ missing'}",
             unsafe_allow_html=True)
    st.caption("Keys project ki .env file mein saved hain. Yahan override kar sakte ho:")
    pex_ov = st.text_input("Pexels key override", type="password")
    pix_ov = st.text_input("Pixabay key override", type="password")
    cov_ov = st.text_input("Coverr key override (free: coverr.co/developers)", type="password")
    if pex_ov:
        keys["pexels"] = pex_ov
    if pix_ov:
        keys["pixabay"] = pix_ov
    if cov_ov:
        keys["coverr"] = cov_ov

# ---------- build ----------
if st.button("🚀 Video banao", type="primary", disabled=audio is None):
    work_dir = tempfile.mkdtemp(prefix="voicecut_")
    up_path = os.path.join(work_dir, "upload_" + audio.name)
    with open(up_path, "wb") as f:
        f.write(audio.read())
    music_path = None
    if music_up:
        music_path = os.path.join(work_dir, "music_" + music_up.name)
        with open(music_path, "wb") as f:
            f.write(music_up.read())

    status = st.empty()
    bar = st.progress(0)

    def _progress(text, frac):
        status.write(text)
        bar.progress(min(1.0, frac))

    try:
        result = run_pipeline(up_path, os.path.join(work_dir, "work"),
                              ratio=ratio, keys=keys,
                              music_path=music_path, auto_music=auto_music,
                              sfx_on=sfx_on, progress=_progress)
        st.session_state["vc"] = {"work_dir": os.path.join(work_dir, "work"),
                                  "final": result["final"],
                                  "report": result["scenes"],
                                  "duration": result["duration"],
                                  "ratio": ratio, "chunks": result["chunks"],
                                  "music": result["music"]}
        st.success(f"✅ Tayyar! {result['chunks']} clips, "
                   f"{result['duration']:.0f} second — voice-over jitni lambi, video utni lambi.")
    except Exception as e:  # noqa: BLE001
        st.error(f"❌ Error: {e}")

# ---------- preview + volume + download ----------
vc = st.session_state.get("vc")
if vc:
    st.divider()
    st.subheader("👀 Preview")
    st.video(vc["final"])

    st.subheader("🔊 Sound adjust karo")
    mvol = st.slider("Background music volume", 0, 100, 25)
    svol = st.slider("Sound effects volume", 0, 100, 35)
    if st.button("🎚️ Sound update karo"):
        with st.spinner("Mix ho raha hai..."):
            new_final = remix_audio(vc["work_dir"], mvol / 100, svol / 100,
                                    out_name="final_remix.mp4")
            vc["final"] = new_final
            st.session_state["vc"] = vc
        st.success("✅ Sound update ho gaya!")

    with open(vc["final"], "rb") as f:
        st.download_button("⬇️ HD Video download karo (MP4)", f,
                           file_name=f"voicecut_{vc['ratio'].replace(':', 'x')}.mp4",
                           mime="video/mp4", type="primary")

    with st.expander(f"🎞️ Clip report ({vc['chunks']} clips)"):
        for r in vc["report"]:
            st.write(f"**Clip {r['clip']}** [{r['start']}s, {r['duration']}s] — "
                     f"`{r['query']}` → {r['visual']} ({r['credit']})")
            st.caption(r["text"] + "…")

st.divider()
st.caption("Sources: YouTube · Pexels · Pixabay · Coverr — "
           "har clip max 4 second, video duration = voice-over duration.")
