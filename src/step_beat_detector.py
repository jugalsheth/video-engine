from __future__ import annotations

"""
Detect CapCut-style step punch beats from speech ("step 1", "step one", etc.).
Primary source: STEP_REVEAL shots in the shot list (script + transcript aligned).
Fallback: scan transcript for step markers when shots are missing.
"""

import json
from pathlib import Path

from src.frame_utils import frame_for_phrase, normalize
from src.shot_planner import STEP_PHRASE_ALIASES, _detect_steps, _step_number_token

PUNCH_LEAD_FRAMES = 0  # punch exactly when step is spoken


def _beats_from_shots(shot_list: dict) -> list[dict]:
    beats: list[dict] = []
    for shot in shot_list.get("shots", []):
        if shot.get("type") != "STEP_REVEAL":
            continue
        params = shot.get("params", {})
        beats.append({
            "step": params.get("step_number", len(beats) + 1),
            "frame": max(0, shot["start_frame"] + PUNCH_LEAD_FRAMES),
            "label": params.get("text", ""),
            "source": params.get("source", "shot_list"),
        })
    return sorted(beats, key=lambda b: b["frame"])


def _beats_from_transcript(transcript: dict) -> list[dict]:
    words = transcript.get("words", [])
    full_text = transcript.get("full_text", "")
    beats: list[dict] = []
    for i, w in enumerate(words):
        prev = normalize(words[i - 1].get("word", "")) if i > 0 else ""
        if prev not in {"step", "steps"}:
            continue
        num = _step_number_token(w.get("word", ""))
        if num is None:
            continue
        beats.append({
            "step": num,
            "frame": w["start_frame"],
            "label": f"STEP {num}",
            "source": "transcript",
        })
    # also try script-style phrases
    for phrase, aliases in STEP_PHRASE_ALIASES.items():
        num = _step_number_token(phrase.split()[-1])
        if num is None:
            continue
        for alias in aliases:
            frame = frame_for_phrase(words, full_text, alias)
            if frame is not None:
                if not any(b["step"] == num for b in beats):
                    beats.append({
                        "step": num,
                        "frame": frame,
                        "label": f"STEP {num}",
                        "source": "transcript_phrase",
                    })
                break
    return sorted(beats, key=lambda b: b["frame"])


def detect(transcript: dict, shot_list: dict) -> dict:
    beats = _beats_from_shots(shot_list)
    if not beats:
        beats = _beats_from_transcript(transcript)
    return {
        "beats": beats,
        "summary": {
            "count": len(beats),
            "steps": [b["step"] for b in beats],
            "source": beats[0]["source"] if beats else "none",
        },
    }


def save(result: dict, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2))
    return path
