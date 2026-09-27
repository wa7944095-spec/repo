"""VoiceCut Studio — voice-over se auto-edited video banane wala tool."""

import os as _os

# httpx (huggingface_hub ke andar) no_proxy mein bracketed IPv6 entries
# jaisay [::1] par crash karta hai ("Invalid port"). Sirf simple hosts rakho.
for _var in ("no_proxy", "NO_PROXY"):
    _val = _os.environ.get(_var, "")
    if _val:
        _clean = ",".join(
            p for p in _val.split(",") if not p.strip().startswith("["))
        _os.environ[_var] = _clean
