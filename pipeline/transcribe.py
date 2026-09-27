"""Step 1 — Voice-over ko transcribe karo aur timed scenes mein divide karo.

faster-whisper (local, free) audio ko sun kar har jumle ke
start/end timestamps nikalta hai. Phir chhote segments ko
jod kar scenes banaye jate hain taake har scene itna lamba ho
ke us par ek visual clip lag sake.
"""

import os

from faster_whisper import WhisperModel

_model = None

# Project ke saath bundled local model (hub download ki zaroorat nahi)
_LOCAL_MODEL = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "models", "base")


def _get_model(model_size="base"):
    global _model
    if _model is None:
        # int8 = tez + halka; CPU par bhi theek chalta hai
        model_id = (_LOCAL_MODEL if os.path.isfile(
            os.path.join(_LOCAL_MODEL, "model.bin")) else model_size)
        try:
            _model = WhisperModel(model_id, device="cpu", compute_type="int8")
        except Exception:
            # Network approval na mile to cached model offline use karo
            os.environ["HF_HUB_OFFLINE"] = "1"
            _model = WhisperModel(model_id, device="cpu", compute_type="int8")
    return _model


def transcribe(audio_path, model_size="base", min_scene_secs=6.0,
               max_scene_secs=20.0):
    """Returns dict: {duration, language, scenes:[{start,end,text}]}"""
    model = _get_model(model_size)
    segments, info = model.transcribe(audio_path, beam_size=5)

    raw = [(s.start, s.end, s.text.strip()) for s in segments if s.text.strip()]
    if not raw:
        raise ValueError("Audio mein koi speech nahi mili — file check karo.")

    scenes = []
    cur, cur_start = [], None
    for start, end, text in raw:
        if cur_start is None:
            cur_start = start
        cur.append(text)
        dur = end - cur_start
        ends_sentence = text.rstrip().endswith((".", "!", "?", "…", "।"))
        if (dur >= min_scene_secs and ends_sentence) or dur >= max_scene_secs:
            scenes.append({"start": cur_start, "end": end, "text": " ".join(cur)})
            cur, cur_start = [], None
    if cur:
        scenes.append({"start": cur_start, "end": raw[-1][1], "text": " ".join(cur)})

    return {
        "duration": info.duration,
        "language": info.language,
        "scenes": scenes,
    }
