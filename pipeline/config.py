"""API keys .env se load karo (project folder mein, kahin share nahi hoti)."""

import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_keys():
    keys = {
        "pexels": os.environ.get("PEXELS_API_KEY"),
        "pixabay": os.environ.get("PIXABAY_API_KEY"),
        "coverr": os.environ.get("COVERR_API_KEY"),
    }
    env_path = os.path.join(_ROOT, ".env")
    if os.path.isfile(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip()
                if k == "PEXELS_API_KEY" and not keys["pexels"]:
                    keys["pexels"] = v
                elif k == "PIXABAY_API_KEY" and not keys["pixabay"]:
                    keys["pixabay"] = v
                elif k == "COVERR_API_KEY" and not keys["coverr"]:
                    keys["coverr"] = v
    return keys
