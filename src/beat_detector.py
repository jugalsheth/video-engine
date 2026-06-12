from __future__ import annotations

import json
import re
from pathlib import Path

from src.frame_utils import frame_for_phrase

HOOK_PHRASES = [
    "about to show you",
    "about to show",
    "about to break",
    "break it down",
    "break this down",
    "here's what's wild",
    "here's what's",
    "here's how",
    "here's the",
    "let me show",
    "going to break",
    "the truth is",
    "step one",
    "that's the secret",
    "here's the difference",
]

MIN_PAUSE_FRAMES = 4
EARLY_SCAN_SECONDS = 12
MAX_CRUST_SECONDS = 15
THREE_STEP_MAX_CRUST_SECONDS = 8.0
THREE_STEP_CRUST_TARGET_SECONDS = 5.5
MIN_CRUST_SECONDS = 2.5


def _normalize(text: str) -> str:
    t = text.lower()
    t = re.sub(r"\ba\s*\.?\s*m\.?", "am", t)
    t = re.sub(r"\bp\s*\.?\s*m\.?", "pm", t)
    return re.sub(r"[^a-z0-9' ]", "", t)


def _hook_end_frame(words: list, full_text: str, phrase: str) -> int:
    idx = full_text.find(phrase)
    if idx == -1:
        return 0
    end_idx = idx + len(phrase)
    char_pos = 0
    end_frame = words[0]["end_frame"] if words else 0
    for w in words:
        token = re.sub(r"[^a-z0-9']", "", w.get("word", "").lower())
        if char_pos < end_idx and token:
            end_frame = w["end_frame"]
        char_pos += len(token) + 1
    return end_frame


def _find_hook_end(full_text: str, words: list) -> int | None:
    best: int | None = None
    for phrase in sorted(HOOK_PHRASES, key=len, reverse=True):
        if phrase not in full_text:
            continue
        end = _hook_end_frame(words, full_text, phrase)
        if best is None or end < best:
            best = end
    return best


def _first_pause_after(
    words: list,
    after_frame: int,
    fps: int,
    max_seconds: float = 2.0,
) -> tuple[int | None, int]:
    limit = after_frame + int(max_seconds * fps)
    for i in range(len(words) - 1):
        w, nxt = words[i], words[i + 1]
        if w["end_frame"] < after_frame:
            continue
        if nxt["start_frame"] > limit:
            break
        gap = nxt["start_frame"] - w["end_frame"]
        if gap >= MIN_PAUSE_FRAMES:
            return nxt["start_frame"], gap
    return None, 0


def _largest_early_pause(words: list, fps: int, max_seconds: float = EARLY_SCAN_SECONDS) -> tuple[int | None, int]:
    limit = int(max_seconds * fps)
    best_gap = 0
    best_start = None
    for i in range(len(words) - 1):
        if words[i]["start_frame"] > limit:
            break
        gap = words[i + 1]["start_frame"] - words[i]["end_frame"]
        if gap >= MIN_PAUSE_FRAMES and gap > best_gap:
            best_gap = gap
            best_start = words[i + 1]["start_frame"]
    return best_start, best_gap


def _opening_sentence_end(words: list, fps: int) -> int:
    """End of ~first clause for growth hooks without 'break it down'."""
    if not words:
        return int(3 * fps)
    target_words = min(16, len(words))
    return words[target_words - 1]["end_frame"]


def _max_crust_seconds(script: dict | None) -> float:
    template_id = (script or {}).get("edit_template") or ""
    if template_id == "THREE_STEP_HOT_TAKE":
        return THREE_STEP_MAX_CRUST_SECONDS
    return MAX_CRUST_SECONDS


def _clamp_crust(
    crust: int, hook_end: int | None, fps: int, script: dict | None = None
) -> tuple[int, int]:
    max_seconds = _max_crust_seconds(script)
    max_frame = int(max_seconds * fps)
    min_frame = int(MIN_CRUST_SECONDS * fps)
    template_id = (script or {}).get("edit_template") or ""
    if template_id == "THREE_STEP_HOT_TAKE" and crust > max_frame:
        crust = int(THREE_STEP_CRUST_TARGET_SECONDS * fps)
    crust = min(max(crust, min_frame), max_frame)
    hook = hook_end if hook_end is not None else max(0, crust - int(0.35 * fps))
    hook = min(hook, crust - 5)
    hook = max(0, hook)
    return hook, crust


def detect(transcript: dict, script: dict | None = None) -> dict:
    """
    Reels/TikTok beat map — crust punch MUST land in first 15s.
    """
    words = transcript.get("words", [])
    fps = transcript.get("fps", 30)
    full_text = _normalize(transcript.get("full_text", ""))
    max_crust_frame = int(_max_crust_seconds(script) * fps)

    hook_end = _find_hook_end(full_text, words)
    pause_start, pause_frames = _largest_early_pause(words, fps)

    crust_start: int | None = None

    if hook_end is not None:
        after_hook, gap = _first_pause_after(words, hook_end, fps)
        if after_hook is not None:
            crust_start = after_hook
            pause_frames = gap
        else:
            crust_start = hook_end + int(0.2 * fps)
            pause_frames = int(0.2 * fps)
    elif pause_start is not None:
        crust_start = pause_start
        hook_end = max(0, pause_start - int(0.4 * fps))
    else:
        opening_end = _opening_sentence_end(words, fps)
        hook_end = opening_end
        crust_start = opening_end + int(0.25 * fps)
        pause_frames = int(0.25 * fps)

    # Script crust phrase — only if it lands in the first 15s (never end-of-video)
    if script:
        triggers = script.get("video_triggers") or {}
        beat_phrases = triggers.get("beat_phrases") or {}
        crust_phrase = beat_phrases.get("crust") or beat_phrases.get("energy")

        # recording_cues with crust phrase override beat_phrases timing
        for cue in script.get("recording_cues") or []:
            phrase = cue.get("phrase")
            action = (cue.get("action") or "").upper()
            if not phrase or ("CRUST" not in action and "ENERGY UP" not in action):
                continue
            crust_frame = frame_for_phrase(
                words, transcript.get("full_text", ""), phrase
            )
            if crust_frame is not None and crust_frame <= max_crust_frame:
                crust_start = crust_frame
                hook_end = max(0, crust_frame - int(0.35 * fps))
                pause_frames = int(0.15 * fps)
                crust_phrase = None  # already handled via cue
                break

        if crust_phrase:
            crust_frame = frame_for_phrase(
                words, transcript.get("full_text", ""), crust_phrase
            )
            if crust_frame is not None and crust_frame <= max_crust_frame:
                crust_start = crust_frame
                hook_end = max(0, crust_frame - int(0.35 * fps))
                pause_frames = int(0.15 * fps)

        delivery = script.get("delivery_notes") or ""
        for match in re.finditer(
            r"(?:energy|pick up|speed up|emphasize)\s+(?:at|on)\s+['\"]?([^'\".;]+)",
            delivery,
            re.I,
        ):
            phrase = match.group(1).strip()
            frame = frame_for_phrase(words, transcript.get("full_text", ""), phrase)
            if frame is not None and frame <= max_crust_frame:
                crust_start = frame
                hook_end = max(0, frame - int(0.35 * fps))
                break

        payoff_phrase = beat_phrases.get("payoff")
        if payoff_phrase:
            payoff_frame = frame_for_phrase(
                words, transcript.get("full_text", ""), payoff_phrase
            )
            if payoff_frame is not None:
                transcript["_payoff_frame"] = payoff_frame

    hook_end, crust_start = _clamp_crust(
        crust_start or int(4 * fps), hook_end, fps, script
    )

    return {
        "hook_start": 0,
        "hook_end": hook_end,
        "crust_start": crust_start,
        "pause_frames": pause_frames,
        "setup_zoom": 1.04,
        "crust_zoom_peak": 1.32,
        "crust_settle": 1.12,
        "summary": {
            "hook_seconds": round(hook_end / fps, 2),
            "crust_seconds": round(crust_start / fps, 2),
            "pause_ms": round((pause_frames / fps) * 1000),
        },
    }


def save(result: dict, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2))
    return path
