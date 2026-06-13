from __future__ import annotations

"""
Deterministic shot list builder.
Uses script visual_moments + video_triggers when matched; transcript regex otherwise.
"""

import re
from pathlib import Path

from src.frame_utils import frame_for_phrase, fuzzy_frame_for_phrase, normalize, words_after_number
from src.template_loader import resolve_template

TITLE_HOOK_FRAMES = 45
STAT_HOLD_FRAMES = 90
STEP_HOLD_FRAMES = 90
ZOOM_HOOK_FRAMES = 32
CLOSER_FRAMES = 90
STAT_MERGE_FRAMES = 30

ORDINAL_MAP = {
    "one": 1,
    "two": 2,
    "three": 3,
    "first": 1,
    "second": 2,
    "third": 3,
}

HOOK_ZOOM = {
    "IDENTITY CALL": 1.18,
    "CONFESSION": 1.22,
    "CONTRARIAN STRIKE": 1.2,
    "OPEN LOOP": 1.19,
    "HOT TAKE": 1.2,
    "INVESTIGATOR": 1.19,
}

TERRITORY_HASHTAGS = {
    "Tech Made Simple": ["#DataEngineering", "#TechCareers", "#AIEngineer", "#ProductionSystems", "#TechLife"],
    "Career + Money": ["#TechCareer", "#CareerAdvice", "#Salary", "#CareerGrowth", "#LinkedIn"],
}

# Legacy visual_cues phrase hints when visual_moments absent
LEGACY_CUE_PHRASES = [
    ("3 am", "3 AM FAILURE", "right"),
    ("3am", "3 AM FAILURE", "right"),
    ("pure building", "PURE BUILDING", "left"),
    ("pipeline", "PIPELINE", "right"),
    ("production", "PRODUCTION", "right"),
    ("that's normal", "THAT'S NORMAL", "right"),
]

AM_PM_FRAGMENTS = {"am", "pm", "a", "m", "p"}


def _zoom_hook_params(intensity: float) -> dict:
    return {
        "snap_frames": 6,
        "hold_frames": 6,
        "ease_frames": 20,
        "peak_scale": intensity,
        "settle_scale": round(intensity - 0.12, 2),
    }


def _base_shots(transcript: dict, title: str, subtitle: str, intensity: float) -> list[dict]:
    total = transcript["total_frames"]
    return [
        {
            "type": "ZOOM_HOOK",
            "start_frame": 0,
            "end_frame": ZOOM_HOOK_FRAMES,
            "params": _zoom_hook_params(intensity),
        },
        {
            "type": "TITLE_CARD",
            "start_frame": 0,
            "end_frame": TITLE_HOOK_FRAMES,
            "params": {"text": title, "subtitle": subtitle, "animation": "slam_up", "phase": "hook"},
        },
        {
            "type": "CAPTION_HIGHLIGHT",
            "start_frame": 0,
            "end_frame": total,
            "params": {"auto": True},
        },
    ]


def _is_bad_stat_token(token: str, words: list, idx: int) -> bool:
    clean = re.sub(r"[^\d%]", "", token.strip())
    if not clean:
        return True
    if token.strip() in {"!", ".", ",", "-"}:
        return True
    norm = normalize(token)
    if norm in AM_PM_FRAGMENTS:
        return True
    if norm in {"am", "pm"}:
        return True
    # Whisper splits "3 AM" into fragments — skip lone letters near time words
    if len(norm) <= 2 and norm.isalpha():
        neighbors = []
        for j in range(max(0, idx - 2), min(len(words), idx + 3)):
            neighbors.append(normalize(words[j].get("word", "")))
        if "am" in neighbors or "pm" in neighbors:
            return True
    num_only = re.sub(r"[^\d]", "", clean)
    if re.fullmatch(r"20\d{2}|19\d{2}", num_only):
        return True
    return False


def _filter_stats(stats: list[dict]) -> list[dict]:
    filtered: list[dict] = []
    for s in stats:
        num = str(s.get("params", {}).get("number", "")).strip()
        if num in {"!", ".", ""}:
            continue
        label = str(s.get("params", {}).get("label", "")).upper()
        if label in {"A .M.", "A M", "P M", "AM AND", "PM AND"}:
            continue
        if re.fullmatch(r"[A-Z]\s*\.?\s*M\.?", label):
            continue
        filtered.append(s)
    return filtered


def _merge_stats_close(stats: list[dict], within: int = STAT_MERGE_FRAMES) -> list[dict]:
    if not stats:
        return []
    sorted_stats = sorted(stats, key=lambda x: x["start_frame"])
    merged: list[dict] = [sorted_stats[0]]
    for s in sorted_stats[1:]:
        prev = merged[-1]
        if s["start_frame"] - prev["start_frame"] <= within:
            prev_num = str(prev.get("params", {}).get("number", ""))
            new_num = str(s.get("params", {}).get("number", ""))
            if prev_num in {"!", "."} and new_num not in {"!", "."}:
                merged[-1] = s
            continue
        merged.append(s)
    return merged


STEP_PHRASE_ALIASES: dict[str, list[str]] = {
    "step one": ["step one", "step 1", "step 1."],
    "step two": ["step two", "step 2", "step 2."],
    "step three": ["step three", "step 3", "step 3."],
}


def _flex_frame(
    words: list,
    full_text: str,
    phrase: str,
    min_frame: int = 0,
    *,
    allow_fuzzy: bool = True,
) -> int | None:
    """Try full phrase, then trailing words — handles Whisper drift from script."""
    candidates = [phrase]
    norm = phrase.lower().strip()
    if norm in STEP_PHRASE_ALIASES:
        candidates = STEP_PHRASE_ALIASES[norm] + [phrase]

    for candidate in candidates:
        frame = frame_for_phrase(words, full_text, candidate)
        if frame is not None and frame >= min_frame:
            return frame

    if norm in STEP_PHRASE_ALIASES:
        return None

    parts = phrase.split()
    for n in (4, 3, 2):
        if len(parts) >= n:
            tail = " ".join(parts[-n:])
            frame = frame_for_phrase(words, full_text, tail)
            if frame is not None and frame >= min_frame:
                return frame

    if allow_fuzzy:
        frame = fuzzy_frame_for_phrase(words, phrase)
        if frame is not None and frame >= min_frame:
            return frame
    return None


def _stat_shot(
    frame: int,
    number: str,
    label: str,
    side: str,
    source: str = "script",
) -> dict:
    return {
        "type": "STAT_CALLOUT",
        "start_frame": frame,
        "end_frame": frame + STAT_HOLD_FRAMES,
        "params": {
            "number": number,
            "label": label,
            "position": side,
            "source": source,
        },
    }


def _stats_from_visual_moments(script: dict, transcript: dict) -> list[dict]:
    words = transcript.get("words", [])
    full_text = transcript.get("full_text", "")
    stats: list[dict] = []
    for moment in script.get("visual_moments") or []:
        if not isinstance(moment, dict):
            continue
        if moment.get("type", "stat") != "stat":
            continue
        phrase = moment.get("at_phrase", "")
        if not phrase:
            continue
        frame = _flex_frame(words, full_text, phrase)
        if frame is None:
            continue
        graphic = str(moment.get("graphic", "!"))
        label = str(moment.get("label", "HIGHLIGHT")).upper()
        side = moment.get("side", "right" if len(stats) % 2 == 0 else "left")
        stats.append(_stat_shot(frame, graphic, label, side, "visual_moments"))
    return stats


def _stats_from_video_triggers(script: dict, transcript: dict) -> list[dict]:
    words = transcript.get("words", [])
    full_text = transcript.get("full_text", "")
    triggers = script.get("video_triggers") or {}
    stats: list[dict] = []
    for item in triggers.get("stat_phrases") or []:
        if not isinstance(item, dict):
            continue
        phrase = item.get("phrase", "")
        if not phrase:
            continue
        alternates = item.get("alternates") or []
        frame = None
        for candidate in [phrase, *alternates]:
            frame = _flex_frame(words, full_text, candidate)
            if frame is not None:
                break
        if frame is None:
            continue
        display = str(item.get("display", "!"))
        label = str(item.get("label", "STAT")).upper()
        side = item.get("side", "right" if len(stats) % 2 == 0 else "left")
        stats.append(_stat_shot(frame, display, label, side, "stat_phrases"))
    return stats


def _infer_from_legacy_cues(script: dict, transcript: dict) -> list[dict]:
    cues = (script.get("visual_cues") or "").lower()
    if not cues:
        return []
    words = transcript.get("words", [])
    full_text = transcript.get("full_text", "")
    stats: list[dict] = []
    for phrase, label, side in LEGACY_CUE_PHRASES:
        if phrase not in cues:
            continue
        frame = _flex_frame(words, full_text, phrase)
        if frame is None:
            continue
        number = label.split()[0] if label and label[0].isdigit() else "!"
        if number == "3" and "AM" in label:
            number = "3"
        stats.append(_stat_shot(frame, number, label, side, "legacy_cues"))
    return stats


def _detect_stats(words: list) -> list[dict]:
    stats: list[dict] = []
    seen_frames: set[int] = set()
    for i, w in enumerate(words):
        token = w.get("word", "").strip()
        if _is_bad_stat_token(token, words, i):
            continue
        clean = re.sub(r"[^\d%]", "", token)
        if not clean or not re.search(r"\d", clean):
            continue
        num_only = clean.replace("%", "")
        if len(num_only) > 4 and "%" not in token:
            continue
        if re.fullmatch(r"20\d{2}|19\d{2}", num_only):
            continue
        frame = w["start_frame"]
        if frame in seen_frames:
            continue
        seen_frames.add(frame)
        label = words_after_number(words, i)
        stats.append(_stat_shot(
            frame,
            token.replace(",", ""),
            label,
            "right" if len(stats) % 2 == 0 else "left",
            "transcript_regex",
        ))
    return stats


def _step_number_token(token: str) -> int | None:
    norm = normalize(token)
    if norm in ORDINAL_MAP:
        return ORDINAL_MAP[norm]
    digits = re.sub(r"[^\d]", "", token)
    if digits in {"1", "2", "3"}:
        return int(digits)
    return None


def _steps_from_visual_moments(script: dict, transcript: dict) -> list[dict]:
    words = transcript.get("words", [])
    full_text = transcript.get("full_text", "")
    steps: list[dict] = []
    min_frame = 0
    for moment in sorted(
        [m for m in (script.get("visual_moments") or []) if isinstance(m, dict) and m.get("type") == "step"],
        key=lambda m: int(str(m.get("graphic", "99")).strip() or "99"),
    ):
        phrase = moment.get("at_phrase", "")
        if not phrase:
            continue
        frame = _flex_frame(words, full_text, phrase, min_frame=min_frame, allow_fuzzy=False)
        if frame is None:
            continue
        min_frame = frame + 30
        graphic = str(moment.get("graphic", "")).strip()
        num = len(steps) + 1
        if graphic.isdigit():
            num = int(graphic)
        label = str(moment.get("label", f"STEP {num}")).upper()
        steps.append({
            "type": "STEP_REVEAL",
            "start_frame": frame,
            "end_frame": frame + STEP_HOLD_FRAMES,
            "params": {
                "step_number": num,
                "text": label,
                "source": "visual_moments",
            },
        })
    return sorted(steps, key=lambda s: s["start_frame"])


def _detect_steps(words: list) -> list[dict]:
    """Fallback: only match 'step one' / 'step 1.' — not bare ordinals in hook."""
    steps: list[dict] = []
    for i, w in enumerate(words):
        prev = normalize(words[i - 1].get("word", "")) if i > 0 else ""
        if prev not in {"step", "steps"}:
            continue
        num = _step_number_token(w.get("word", ""))
        if num is None or num != len(steps) + 1:
            continue
        text_parts: list[str] = []
        for nw in words[i + 1 : i + 8]:
            t = nw.get("word", "").strip()
            if not t:
                continue
            if normalize(t) in {"step", "steps"}:
                break
            text_parts.append(t)
        step_text = " ".join(text_parts)[:36].upper().rstrip("., ") or f"STEP {num}"
        frame = w["start_frame"]
        steps.append({
            "type": "STEP_REVEAL",
            "start_frame": frame,
            "end_frame": frame + STEP_HOLD_FRAMES,
            "params": {"step_number": num, "text": step_text, "source": "transcript"},
        })
    return steps


def _resolve_steps(script: dict | None, transcript: dict) -> list[dict]:
    words = transcript.get("words", [])
    script_steps = _steps_from_visual_moments(script, transcript) if script else []
    fallback = _detect_steps(words)
    if not script_steps:
        return fallback
    used_nums = {s["params"]["step_number"] for s in script_steps}
    for step in fallback:
        num = step["params"]["step_number"]
        if num not in used_nums:
            script_steps.append(step)
    return sorted(script_steps, key=lambda s: s["start_frame"])


def _energy_highlights(words: list, script: dict | None = None) -> list[dict]:
    default_energy = {"right", "unless", "listen", "that's", "wait", "but", "now", "truth"}
    if script:
        triggers = script.get("video_triggers") or {}
        custom = triggers.get("energy_words") or []
        if custom:
            default_energy = {normalize(w) for w in custom}
    highlights: list[dict] = []
    for w in words:
        if normalize(w.get("word", "")) not in default_energy:
            continue
        frame = w["start_frame"]
        highlights.append({
            "type": "WORD_HIGHLIGHT",
            "start_frame": frame,
            "end_frame": frame + 12,
            "params": {"word": w["word"]},
        })
    return highlights


def _merge_stats(*groups: list[dict]) -> list[dict]:
    merged: list[dict] = []
    used: set[int] = set()
    for group in groups:
        for s in sorted(group, key=lambda x: x["start_frame"]):
            if s["start_frame"] in used:
                continue
            used.add(s["start_frame"])
            merged.append(s)
    return sorted(merged, key=lambda x: x["start_frame"])


def _resolve_script_stats(script: dict, transcript: dict) -> list[dict]:
    """Script-first stats; regex only fills gaps when script has no matches."""
    script_stats = _merge_stats(
        _stats_from_visual_moments(script, transcript),
        _stats_from_video_triggers(script, transcript),
    )
    if not script_stats and not script.get("visual_moments"):
        script_stats = _infer_from_legacy_cues(script, transcript)

    if script_stats:
        return _filter_stats(_merge_stats_close(script_stats))

    has_script_stat_defs = any(
        isinstance(m, dict) and m.get("type") == "stat"
        for m in (script.get("visual_moments") or [])
    ) or bool((script.get("video_triggers") or {}).get("stat_phrases"))

    if has_script_stat_defs:
        return []

    regex_stats = _detect_stats(transcript.get("words", []))
    return _filter_stats(_merge_stats_close(regex_stats))


CUSTOM_VISUAL_HOLD_FRAMES = 90


def _custom_visual_shots(script: dict, transcript: dict) -> tuple[list[dict], list[tuple[int, int]]]:
    """Match custom_visual_overrides to transcript; reserve segments for detectors."""
    overrides = script.get("custom_visual_overrides") or []
    if not overrides:
        return [], []

    words = transcript.get("words", [])
    full_text = transcript.get("full_text", "")
    script_id = Path(script.get("filename_hint", "script")).stem
    shots: list[dict] = []
    reserved: list[tuple[int, int]] = []

    for override in overrides:
        trigger = override.get("trigger_phrase", "")
        if not trigger:
            continue
        frame = frame_for_phrase(words, full_text, trigger)
        if frame is None:
            frame = fuzzy_frame_for_phrase(words, trigger)
        if frame is None:
            continue

        end_frame = min(
            frame + CUSTOM_VISUAL_HOLD_FRAMES,
            transcript.get("total_frames", frame + CUSTOM_VISUAL_HOLD_FRAMES),
        )
        asset_status = override.get("asset_status", "needs_creation")
        asset_path = f"custom_assets/{script_id}/"
        shots.append({
            "type": "CUSTOM_VISUAL",
            "start_frame": frame,
            "end_frame": end_frame,
            "params": {
                "trigger_phrase": trigger,
                "description": override.get("description", ""),
                "asset_status": asset_status,
                "asset_path": asset_path,
                "source": "custom_visual_overrides",
            },
        })
        reserved.append((frame, end_frame))

    return shots, reserved


def from_script(transcript: dict, script: dict) -> dict:
    title = script.get("title_overlay", "UNTITLED")
    subtitle = script.get("subtitle_overlay", "")
    hook_type = script.get("hook_type", "IDENTITY CALL")
    intensity = HOOK_ZOOM.get(hook_type, 1.18)
    total = transcript["total_frames"]

    shots = _base_shots(transcript, title, subtitle, intensity)
    custom_shots, reserved_ranges = _custom_visual_shots(script, transcript)
    shots.extend(custom_shots)
    stats = _resolve_script_stats(script, transcript)
    shots.extend(stats)
    shots.extend(_resolve_steps(script, transcript))
    shots.extend(_energy_highlights(transcript.get("words", []), script))

    closer_start = max(0, total - CLOSER_FRAMES)
    shots.append({
        "type": "ZOOM_CLOSER",
        "start_frame": closer_start,
        "end_frame": total,
        "params": {"start_scale": 1.1, "end_scale": intensity},
    })

    territory = script.get("territory", "general")
    hashtags = script.get("hashtags", TERRITORY_HASHTAGS.get(territory, ["#CareerTips", "#Reels"]))
    template = resolve_template(script)

    return {
        "video_title": title,
        "territory": territory,
        "total_frames": total,
        "fps": transcript.get("fps", 30),
        "caption_for_posting": script.get("caption_hook", transcript.get("full_text", "")[:120]),
        "hashtags": hashtags,
        "shots": shots,
        "edit_template": script.get("edit_template") or template.get("id", "THREE_STEP_HOT_TAKE"),
        "script_metadata": {
            "visual_moments": script.get("visual_moments", []),
            "video_triggers": script.get("video_triggers", {}),
            "delivery_notes": script.get("delivery_notes"),
            "retention_notes": script.get("retention_notes"),
            "recording_cues": script.get("recording_cues", []),
            "edit_template": script.get("edit_template") or template.get("id"),
            "custom_visual_overrides": script.get("custom_visual_overrides", []),
            "reserved_ranges": reserved_ranges,
        },
    }


def from_transcript(transcript: dict) -> dict:
    words = transcript.get("words", [])
    title_words = [w.get("word", "") for w in words[:6]]
    title = " ".join(title_words).upper()[:60] or "UNTITLED"
    total = transcript["total_frames"]
    first_sentence = transcript.get("full_text", "").split(".")[0][:120]

    shots = _base_shots(transcript, title, "", 1.18)
    stats = _filter_stats(_merge_stats_close(_detect_stats(words)))
    shots.extend(stats)
    shots.extend(_resolve_steps(None, transcript))
    shots.extend(_energy_highlights(words))

    closer_start = max(0, total - CLOSER_FRAMES)
    shots.append({
        "type": "ZOOM_CLOSER",
        "start_frame": closer_start,
        "end_frame": total,
        "params": {"start_scale": 1.1, "end_scale": 1.18},
    })

    return {
        "video_title": title,
        "territory": "general",
        "total_frames": total,
        "fps": transcript.get("fps", 30),
        "caption_for_posting": first_sentence,
        "hashtags": ["#CareerTips", "#TechCareers", "#Reels", "#LinkedIn", "#Growth"],
        "shots": shots,
    }


def generate(transcript: dict, script: dict | None) -> dict:
    if script:
        shot_list = from_script(transcript, script)
    else:
        shot_list = from_transcript(transcript)
    script_stats = sum(
        1 for s in shot_list["shots"]
        if s.get("type") == "STAT_CALLOUT"
        and s.get("params", {}).get("source") in {"visual_moments", "stat_phrases", "legacy_cues"}
    )
    print(f"   Shot planner: {len(shot_list['shots'])} shots (deterministic, {script_stats} script-sourced stats)")
    print(f"   Title: {shot_list.get('video_title', 'untitled')}")
    return shot_list
