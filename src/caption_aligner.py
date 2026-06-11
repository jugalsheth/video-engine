from __future__ import annotations

"""
Align Whisper word text to matched script spoken_script.
Keeps Whisper timestamps; replaces display words with script truth.
"""

import re
from difflib import SequenceMatcher

# Spoken → display tokens (order: longer phrases first)
_SPOKEN_NUMBER_REPLACEMENTS: list[tuple[str, str]] = [
    (r"twenty\s+twenty[-\s]+six", "2026"),
    (r"twenty\s+twenty[-\s]+five", "2025"),
    (r"twenty\s+twenty[-\s]+four", "2024"),
    (r"twenty\s+twenty[-\s]+three", "2023"),
    (r"twenty\s+twenty[-\s]+two", "2022"),
    (r"twenty\s+twenty[-\s]+one", "2021"),
    (r"twenty\s+twenty", "2020"),
    (r"eighty\s+percent", "80%"),
    (r"seventy[-\s]+four\s+percent", "74%"),
    (r"seventy\s+four\s+percent", "74%"),
    (r"forty[-\s]+seven\s+percent", "47%"),
    (r"forty\s+seven\s+percent", "47%"),
    (r"five\s+hundred", "500"),
    (r"three\s+am", "3am"),
]


def _normalize_token(token: str) -> str:
    return re.sub(r"[^a-z0-9%]", "", token.lower())


def _script_tokens(spoken: str) -> list[str]:
    text = spoken.lower().strip()
    for pattern, repl in _SPOKEN_NUMBER_REPLACEMENTS:
        text = re.sub(pattern, repl, text, flags=re.I)
    return re.findall(r"[a-z0-9%]+", text)


def _whisper_tokens(words: list) -> list[str]:
    return [_normalize_token(w.get("word", "")) for w in words]


def _map_block(i1: int, i2: int, j1: int, j2: int, script_tokens: list[str]) -> dict[int, str]:
    mapping: dict[int, str] = {}
    span_i = max(i2 - i1, 1)
    span_j = max(j2 - j1, 1)
    for i in range(i1, i2):
        j_off = min(int((i - i1) * span_j / span_i), span_j - 1)
        mapping[i] = script_tokens[j1 + j_off]
    return mapping


def align(transcript: dict, script: dict | None) -> dict:
    if not script:
        return transcript

    spoken = script.get("spoken_script") or ""
    script_tokens = _script_tokens(spoken)
    words = transcript.get("words") or []
    if not script_tokens or not words:
        return transcript

    whisper_toks = _whisper_tokens(words)
    sm = SequenceMatcher(None, whisper_toks, script_tokens, autojunk=False)
    mapping: dict[int, str] = {}

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for i in range(i1, i2):
                mapping[i] = script_tokens[j1 + (i - i1)]
        elif tag == "replace":
            mapping.update(_map_block(i1, i2, j1, j2, script_tokens))

    if not mapping:
        return transcript

    aligned_words: list[dict] = []
    fixes = 0
    for i, w in enumerate(words):
        new_w = dict(w)
        if i in mapping:
            display = mapping[i]
            orig = _normalize_token(w.get("word", ""))
            if display and display != orig:
                fixes += 1
                # Keep trailing punctuation from Whisper (. , ?)
                trail = re.search(r"[.,!?;:]+$", w.get("word", ""))
                new_w["word"] = display + (trail.group(0) if trail else "")
            elif display:
                new_w["word"] = display
        aligned_words.append(new_w)

    full_text = " ".join(w["word"] for w in aligned_words)
    full_text = re.sub(r"\s+([.,!?])", r"\1", full_text)

    result = {**transcript, "words": aligned_words, "full_text": full_text}
    if fixes:
        print(f"   Caption align: {fixes} words corrected from script")
    return result
