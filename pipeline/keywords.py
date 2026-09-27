"""Step 2 — Har scene ka matlab samajh kar visual search query banao.

Koi heavy AI model nahi — tez keyword extractor hai jo scene ke
text mein se important alfaaz (nouns/actions) nikal kar
2-4 lafzon ki search query banata hai, jaisay:
    "dark knight rode through the burning village"
        -> "knight burning village"
"""

import re

STOPWORDS = set(
    """a an the and or but of to in on for with as at by from is are was were
    be been being it its this that these those i you he she we they them his her
    our their my your has have had do does did will would can could should shall
    there here what when where who which whom how not no nor so than too very
    just into out up down over under again once all any both each few more most
    other some such only own same me him us""".split()
)

# Roman Urdu / Urdu ke aam alfaaz bhi ignore karo
STOPWORDS |= set(
    """ka ki ke ko se ne mein main aur ya phir bhi hai hain tha thi the thay
    hoga honge wala wali walay apna apni apne usko isko unko jisko yeh woh ye wo
    kya kyon kyun kaise kab kahan kon kis liye par per""".split()
)


def extract_query(text, max_words=4):
    """Scene text -> Pexels search query (e.g. 'knight burning village')."""
    words = re.findall(r"[a-zA-Z']+", text.lower())
    scored = {}
    for w in words:
        w = w.strip("'")
        if len(w) < 3 or w in STOPWORDS:
            continue
        scored[w] = scored.get(w, 0) + 1
    if not scored:
        return "cinematic b-roll"
    ranked = sorted(scored.items(), key=lambda kv: (-kv[1], words.index(kv[0])))
    picks = [w for w, _ in ranked[:max_words]]
    return " ".join(picks)


def scene_mood(text):
    """Scene ke mood ka andaza — future mein color-grade ke kaam aayega."""
    t = text.lower()
    if any(w in t for w in ["battle", "war", "fight", "blood", "dark", "night",
                            "death", "fear", "jang", "khoon", "andhera"]):
        return "dark"
    if any(w in t for w in ["love", "peace", "morning", "spring", "hope",
                            "mohbat", "aman", "subah", "bahaar", "umeed"]):
        return "bright"
    return "neutral"
