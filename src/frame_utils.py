from __future__ import annotations

import re


def normalize(text: str) -> str:
    t = text.lower()
    t = re.sub(r"\ba\s*\.?\s*m\.?", "am", t)
    t = re.sub(r"\bp\s*\.?\s*m\.?", "pm", t)
    t = re.sub(r"(\d)\s+am", r"\1am", t)
    t = re.sub(r"(\d)\s+pm", r"\1pm", t)
    return re.sub(r"[^a-z0-9' ]", "", t)


def frame_for_char_index(words: list, char_index: int) -> int:
    char_pos = 0
    for word_obj in words:
        if char_pos >= char_index:
            return word_obj["start_frame"]
        char_pos += len(word_obj.get("word", "")) + 1
    return words[-1]["start_frame"] if words else 0


def frame_for_phrase(words: list, full_text: str, phrase: str) -> int | None:
    norm_full = normalize(full_text)
    norm_phrase = normalize(phrase)
    idx = norm_full.find(norm_phrase)
    if idx == -1:
        return None
    return frame_for_char_index(words, idx)


def _norm_token(w: str) -> str:
    return normalize(w)


def fuzzy_frame_for_phrase(words: list, phrase: str, min_ratio: float = 0.6) -> int | None:
    """Token-sequence match tolerant of Whisper drift (like Remotion payoff finder)."""
    phrase_words = [_norm_token(w) for w in phrase.split() if len(_norm_token(w)) > 1]
    if not phrase_words:
        return None

    tokens = [_norm_token(w.get("word", "")) for w in words]
    n = len(phrase_words)

    for i in range(max(0, len(tokens) - n + 1)):
        matches = 0
        for j, p in enumerate(phrase_words):
            t = tokens[i + j] if i + j < len(tokens) else ""
            if not t:
                continue
            if t == p or t.startswith(p) or p.startswith(t) or p in t or t in p:
                matches += 1
        if matches >= max(1, int(len(phrase_words) * min_ratio + 0.5)):
            return words[i]["start_frame"]
    return None


def words_after_number(words: list, start_idx: int, count: int = 4) -> str:
    parts: list[str] = []
    for w in words[start_idx + 1 : start_idx + 1 + count]:
        token = w.get("word", "").strip()
        if token and not re.match(r"^[\d%,.$]+$", token):
            parts.append(token.upper())
    return " ".join(parts)[:32] or "STAT"


_STEP_ORDINALS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "first": 1,
    "second": 2,
    "third": 3,
}


def _parse_step_number(token: str) -> int | None:
    norm = normalize(token)
    if norm in _STEP_ORDINALS:
        return _STEP_ORDINALS[norm]
    digits = re.sub(r"[^\d]", "", token)
    if digits in {"1", "2", "3"}:
        return int(digits)
    return None


def frame_for_step_number(words: list, step_number: int) -> int | None:
    """Frame when the step number is spoken (after 'step'), not when 'step' starts."""
    for i, w in enumerate(words):
        prev = normalize(words[i - 1].get("word", "")) if i > 0 else ""
        if prev not in {"step", "steps"}:
            continue
        num = _parse_step_number(w.get("word", ""))
        if num == step_number:
            return w["start_frame"]
    return None
