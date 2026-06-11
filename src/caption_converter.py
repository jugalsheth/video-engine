from __future__ import annotations

"""
Convert transcript words to SRT for posting.
Optional future: @remotion/captions Caption[] format behind CAPTION_ENGINE=tiktok
"""

from pathlib import Path


def _format_ts(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def to_srt(transcript: dict, max_words_per_cue: int = 3) -> str:
    words = transcript.get("words", [])
    if not words:
        return ""

    cues: list[str] = []
    idx = 1
    i = 0
    while i < len(words):
        chunk = words[i : i + max_words_per_cue]
        start = chunk[0]["start"]
        end = chunk[-1]["end"]
        text = " ".join(w["word"] for w in chunk).upper()
        cues.append(
            f"{idx}\n{_format_ts(start)} --> {_format_ts(end)}\n{text}\n"
        )
        idx += 1
        i += max_words_per_cue

    return "\n".join(cues)


def save_srt(transcript: dict, path: Path) -> Path:
    path.write_text(to_srt(transcript))
    return path
