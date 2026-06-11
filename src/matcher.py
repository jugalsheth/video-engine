from __future__ import annotations

"""
Attempts to match a transcript to a script from the archive.
This is OPTIONAL — the pipeline runs with or without a match.
Matching adds: title overlay, caption, hashtags, semantic metadata.
Without a match: design agent works from transcript structure alone.
"""

from difflib import SequenceMatcher
from pathlib import Path


def find(video_path: str, transcript: dict, scripts: list) -> dict | None:
    """
    Two matching strategies:
    1. Filename contains script identifier (e.g. script_03)
    2. Fuzzy match of transcript opening against script opening_lines
    Returns matched script dict or None.
    """
    if not scripts:
        return None

    video_name = Path(video_path).stem.lower()

    for script in scripts:
        script_num = str(script.get("script_number", ""))
        if script_num and f"script_{script_num.zfill(2)}" in video_name:
            print(
                f"   Filename match: Script {script_num} — "
                f"{script.get('title_overlay', '')}"
            )
            return script

    transcript_open = " ".join(transcript["full_text"].split()[:20]).lower()

    best_score = 0
    best_match = None

    for script in scripts:
        script_open = script.get("opening_line", "").lower()
        if not script_open:
            continue
        score = SequenceMatcher(None, transcript_open, script_open).ratio()
        if score > best_score:
            best_score = score
            best_match = script

    if best_score >= 0.55:
        print(
            f"   Fuzzy match ({best_score:.0%}): "
            f"{best_match.get('title_overlay', '')}"
        )
        return best_match

    print("   No script match — transcript-only mode")
    return None
