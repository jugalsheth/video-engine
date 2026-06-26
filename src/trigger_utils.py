from __future__ import annotations

from src.frame_utils import frame_for_phrase, fuzzy_frame_for_phrase, normalize
from src.shot_planner import _flex_frame


def resolve_phrase_frame(
    words: list,
    full_text: str,
    phrase: str,
    *,
    fuzzy: bool = True,
    flex: bool = True,
) -> tuple[int | None, str]:
    """
    Resolve a spoken phrase to a start frame.
    Returns (frame, match_method) where match_method is one of:
    flex, exact, fuzzy, collapsed, none
    """
    if not phrase or not words:
        return None, "none"

    if flex:
        frame = _flex_frame(words, full_text, phrase)
        if frame is not None:
            return frame, "flex"

    frame = frame_for_phrase(words, full_text, phrase)
    if frame is not None:
        return frame, "exact"

    if fuzzy:
        frame = fuzzy_frame_for_phrase(words, phrase)
        if frame is not None:
            return frame, "fuzzy"

    frame = _collapsed_word_window(words, phrase)
    if frame is not None:
        return frame, "collapsed"

    return None, "none"


def phrase_in_transcript(words: list, full_text: str, phrase: str) -> bool:
    frame, _ = resolve_phrase_frame(words, full_text, phrase)
    return frame is not None


def _collapsed_word_window(words: list, phrase: str) -> int | None:
    """Match phrase across split Whisper tokens (e.g. open + ai -> openai)."""
    collapsed_phrase = normalize(phrase).replace(" ", "")
    if len(collapsed_phrase) < 3:
        return None
    max_window = min(6, len(collapsed_phrase) + 2)
    for i in range(len(words)):
        chunk = ""
        for j in range(i, min(i + max_window, len(words))):
            chunk += normalize(words[j].get("word", ""))
            if collapsed_phrase in chunk:
                return words[i]["start_frame"]
            if len(chunk) > len(collapsed_phrase) + 8:
                break
    return None
