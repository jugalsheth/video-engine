from __future__ import annotations

import json
import re
from pathlib import Path

from src.frame_utils import frame_for_char_index, frame_for_phrase, normalize
from src.lottie_assets import fun_lottie_map
from src.rules_loader import load_fun_groups

FUN_DURATION_FRAMES = 42  # 1.4s — snappy CapCut-style
RATE_LIMIT_MEDIUM = 54  # 1.8s at 30fps
RATE_LIMIT_CHAOS = 42  # 1.4s
MAX_FUN_MOMENTS = 10
MIN_KEYWORD_LEN = 5  # skip weak single-word hits like "how"
WEAK_TYPES = {"speech_bubble"}
PREFERRED_TYPES = {"comic_sfx", "manga_lines", "red_x", "fire_spark", "emoji_pop", "mind_blown"}

CHAOS_WORDS = {
    "crazy", "insane", "wild", "fire", "boom", "literally", "actually",
    "secret", "mistake", "fail", "wow", "viral", "explode", "chaos",
}
MEDIUM_WORDS = {
    "truth", "fact", "finally", "done", "hack", "trick", "success",
    "wrong", "really", "money", "salary",
}

CONFLICT_SHOT_TYPES = {"TITLE_CARD", "CUSTOM_VISUAL"}
TITLE_END_BUFFER_FRAMES = 12

EMOJI_MAP = {
    "fire": "🔥",
    "crazy": "🤯",
    "insane": "😱",
    "wild": "🌪️",
    "wow": "😮",
    "literally": "💀",
    "money": "💰",
    "salary": "💵",
    "fail": "❌",
    "wrong": "🚫",
    "secret": "🤫",
    "hack": "💡",
    "really": "❓",
}

LOTTIE_TYPES = {"confetti", "mind_blown", "money_rain", "fire_spark"}


def _occupied_ranges(shot_list: dict) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    for shot in shot_list.get("shots", []):
        if shot.get("type") in CONFLICT_SHOT_TYPES:
            end = shot["end_frame"]
            if shot.get("type") == "TITLE_CARD":
                end += TITLE_END_BUFFER_FRAMES
            ranges.append((shot["start_frame"], end))
    return ranges


def _overlaps(start: int, end: int, ranges: list[tuple[int, int]]) -> bool:
    return any(start < re_ and end > rs for rs, re_ in ranges)


def detect_mood(transcript: dict) -> str:
    text = normalize(transcript.get("full_text", ""))
    tokens = set(text.split())
    chaos_score = len(tokens & CHAOS_WORDS)
    medium_score = len(tokens & MEDIUM_WORDS)
    if re.search(r"\d{2,}", text):
        chaos_score += 1
    if text.count("!") >= 2:
        chaos_score += 1
    energy_ratio = chaos_score / max(len(transcript.get("words", [])), 1) * 100
    if chaos_score >= 3 or energy_ratio > 4 or (chaos_score >= 2 and medium_score >= 2):
        return "chaos"
    return "medium"


def _comic_text(keyword: str, word_obj: dict) -> str:
    raw = word_obj.get("word", keyword).strip().upper()
    if re.search(r"\d", raw):
        return f"{raw}!"
    if len(raw) <= 4:
        return raw
    return "BOOM!"


def _pick_emoji(keyword: str) -> str:
    k = keyword.lower()
    for key, emoji in EMOJI_MAP.items():
        if key in k:
            return emoji
    return "✨"


def _build_moment(fun_type: str, phrase: str, start: int, mood: str, side: str, word_obj: dict) -> dict:
    end = start + FUN_DURATION_FRAMES
    moment: dict = {
        "type": fun_type,
        "start_frame": start,
        "end_frame": end,
        "keyword": phrase,
        "mood": mood,
        "side": side,
    }
    if fun_type == "comic_sfx":
        moment["text"] = _comic_text(phrase, word_obj)
    elif fun_type == "emoji_pop":
        moment["emoji"] = _pick_emoji(phrase)
    elif fun_type == "speech_bubble":
        moment["text"] = phrase.upper()[:24]
    elif fun_type in LOTTIE_TYPES:
        lottie_map = fun_lottie_map()
        if fun_type in lottie_map:
            moment["lottie_file"] = lottie_map[fun_type]
    return moment


def _fun_type_for_phrase(phrase: str, fun_groups: dict) -> str:
    norm_phrase = normalize(phrase)
    for fun_type, (keywords, _) in fun_groups.items():
        if fun_type in WEAK_TYPES:
            continue
        for kw in sorted(keywords, key=len, reverse=True):
            if kw in norm_phrase or norm_phrase in kw:
                return fun_type
    return "comic_sfx"


def _upgrade_type(fun_type: str) -> str:
    if fun_type in WEAK_TYPES:
        return "comic_sfx"
    return fun_type


def _seed_script_fun_phrases(
    script: dict | None,
    transcript: dict,
    fun_groups: dict,
    occupied: list[tuple[int, int]],
    mood: str,
) -> tuple[list[dict], list[tuple[int, int]], int]:
    """Priority fun moments from script video_triggers.fun_phrases."""
    if not script:
        return [], [], 0

    triggers = script.get("video_triggers") or {}
    fun_phrases = triggers.get("fun_phrases") or []
    words = transcript.get("words", [])
    full_text = transcript.get("full_text", "")
    moments: list[dict] = []
    used_spans: list[tuple[int, int]] = []
    side_toggle = 0

    for phrase in fun_phrases:
        if not phrase:
            continue
        norm_phrase = normalize(phrase)
        norm_full = normalize(full_text)
        if norm_phrase not in norm_full:
            continue
        idx = norm_full.find(norm_phrase)
        end_idx = idx + len(norm_phrase)
        start = frame_for_phrase(words, full_text, phrase) or frame_for_char_index(words, idx)
        end = start + FUN_DURATION_FRAMES
        if _overlaps(start, end, occupied):
            continue
        fun_type = _upgrade_type(_fun_type_for_phrase(phrase, fun_groups))
        word_obj = next((w for w in words if w["start_frame"] >= start), words[0] if words else {})
        side = "left" if side_toggle % 2 == 0 else "right"
        side_toggle += 1
        moments.append(_build_moment(fun_type, phrase, start, mood, side, word_obj))
        used_spans.append((idx, end_idx))

    return moments, used_spans, side_toggle


def detect(transcript: dict, shot_list: dict, script: dict | None = None) -> dict:
    words = transcript.get("words", [])
    occupied = _occupied_ranges(shot_list)
    mood = detect_mood(transcript)
    mood_tier = 1 if mood == "chaos" else 0
    rate_limit = RATE_LIMIT_CHAOS if mood == "chaos" else RATE_LIMIT_MEDIUM
    fun_groups = load_fun_groups()

    if script is None:
        script = shot_list.get("script_metadata")

    full_text = normalize(transcript.get("full_text", ""))
    moments: list[dict] = []
    skipped: list[dict] = []

    seeded, used_spans, side_toggle = _seed_script_fun_phrases(
        script, transcript, fun_groups, occupied, mood
    )
    moments.extend(seeded)
    type_counts: dict[str, int] = {}
    for m in seeded:
        type_counts[m["type"]] = type_counts.get(m["type"], 0) + 1

    all_phrases: list[tuple[str, str, int]] = []
    for fun_type, (keywords, min_tier) in fun_groups.items():
        if min_tier > mood_tier:
            continue
        for kw in sorted(keywords, key=len, reverse=True):
            all_phrases.append((fun_type, kw, min_tier))
    all_phrases.sort(key=lambda x: len(x[1]), reverse=True)

    for fun_type, phrase, _ in all_phrases:
        fun_type = _upgrade_type(fun_type)
        if fun_type in WEAK_TYPES:
            continue
        if len(phrase) < MIN_KEYWORD_LEN and " " not in phrase:
            continue
        if type_counts.get(fun_type, 0) >= 2:
            continue
        if phrase not in full_text:
            continue
        idx = full_text.find(phrase)
        end_idx = idx + len(phrase)
        if any(idx < e and end_idx > s for s, e in used_spans):
            continue

        start = frame_for_char_index(words, idx)
        end = start + FUN_DURATION_FRAMES
        if _overlaps(start, end, occupied):
            skipped.append({"type": fun_type, "start_frame": start, "keyword": phrase, "reason": "shot conflict"})
            continue

        word_obj = next((w for w in words if w["start_frame"] >= start), words[0] if words else {})
        side = "left" if side_toggle % 2 == 0 else "right"
        side_toggle += 1

        moments.append(_build_moment(fun_type, phrase, start, mood, side, word_obj))
        type_counts[fun_type] = type_counts.get(fun_type, 0) + 1
        used_spans.append((idx, end_idx))

    # Stat moments → comic pop (pairs with STAT_CALLOUT shots)
    for shot in shot_list.get("shots", []):
        if shot.get("type") != "STAT_CALLOUT":
            continue
        start = shot["start_frame"]
        end = start + FUN_DURATION_FRAMES
        if _overlaps(start, end, occupied):
            continue
        if any(m["start_frame"] == start for m in moments):
            continue
        num = str(shot.get("params", {}).get("number", "!"))
        moments.append({
            "type": "comic_sfx",
            "start_frame": start,
            "end_frame": end,
            "keyword": num,
            "mood": mood,
            "side": "right",
            "text": f"{num}!",
        })

    moments.sort(key=lambda m: m["start_frame"])

    accepted: list[dict] = []
    last_start = -rate_limit
    for m in moments:
        if len(accepted) >= MAX_FUN_MOMENTS:
            skipped.append({**m, "reason": "max moments cap"})
            continue
        if m["start_frame"] < last_start + rate_limit:
            skipped.append({**m, "reason": f"rate limit ({mood})"})
            continue
        accepted.append(m)
        last_start = m["start_frame"]

    return {
        "mood": mood,
        "moments": accepted,
        "skipped": skipped,
        "summary": {
            "detected": len(accepted),
            "skipped": len(skipped),
            "mood": mood,
            "types": [m["type"] for m in accepted],
        },
    }


def save(result: dict, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2))
    return path
