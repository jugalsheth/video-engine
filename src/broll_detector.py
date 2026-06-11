from __future__ import annotations

import json
import re
from pathlib import Path

from src.frame_utils import frame_for_char_index, frame_for_phrase, normalize

BROLL_DURATION_FRAMES = 75
STAGGER_FRAMES = 10
RATE_LIMIT_FRAMES = 240  # max 1 B-roll per 8 seconds at 30fps

GREENSCREEN_TYPES = {"data_flow", "terminal", "linkedin", "salary", "growth_chart"}

KEYWORD_GROUPS: dict[str, list[str]] = {
    "salary": [
        "salary", "money", "pay", "compensation", "raise", "income", "wage", "revenue", "finance",
    ],
    "linkedin": ["linkedin", "profile", "recruiter", "resume", "network", "connection"],
    "checklist": [
        "production system", "do this", "checklist", "action items",
    ],
    "data_flow": [
        "data pipeline", "data pipelines", "production data", "data system",
        "warehouse", "etl", "metrics", "automated workflow", "automated workflows",
    ],
    "terminal": [
        "python script", "writing code", "writing python", "terminal", "git push", "push code",
    ],
    "neural_network": ["machine learning", "neural network", "large language model", "llm model"],
    "growth_chart": ["job interview", "career growth", "got promoted", "promoted", "hired"],
}

SEARCH_QUERIES: dict[str, str] = {
    "salary": "business growth chart money",
    "linkedin": "professional networking phone",
    "checklist": "checklist productivity office",
    "data_flow": "data center server technology",
    "terminal": "coding laptop programmer",
    "neural_network": "artificial intelligence abstract",
    "growth_chart": "career success office professional",
}

CONFLICT_SHOT_TYPES = {"TITLE_CARD"}
TITLE_END_BUFFER_FRAMES = 12


def _occupied_ranges(shot_list: dict) -> list[tuple[int, int, str]]:
    ranges: list[tuple[int, int, str]] = []
    for shot in shot_list.get("shots", []):
        if shot.get("type") in CONFLICT_SHOT_TYPES:
            end = shot["end_frame"]
            if shot.get("type") == "TITLE_CARD":
                end += TITLE_END_BUFFER_FRAMES
            ranges.append((shot["start_frame"], end, shot["type"]))
    return ranges


def _overlaps(start: int, end: int, ranges: list[tuple[int, int, str]]) -> str | None:
    for rs, re_, label in ranges:
        if start < re_ and end > rs:
            return label
    return None


def _broll_type_for_phrase(phrase: str) -> str:
    norm_phrase = normalize(phrase)
    for group_type, keywords in KEYWORD_GROUPS.items():
        for kw in sorted(keywords, key=len, reverse=True):
            if kw in norm_phrase or norm_phrase in kw:
                return group_type
    if "python" in norm_phrase or "script" in norm_phrase:
        return "terminal"
    if "pipeline" in norm_phrase or "data" in norm_phrase:
        return "data_flow"
    if "finance" in norm_phrase or "sales" in norm_phrase:
        return "salary"
    return "data_flow"


def _seed_script_broll_phrases(
    script: dict | None,
    transcript: dict,
    occupied: list[tuple[int, int, str]],
) -> tuple[list[dict], set[str], list[tuple[int, int]]]:
    if not script:
        return [], set(), []

    triggers = script.get("video_triggers") or {}
    broll_phrases = triggers.get("broll_phrases") or []
    words = transcript.get("words", [])
    full_text = transcript.get("full_text", "")
    norm_full = normalize(full_text)
    moments: list[dict] = []
    seen_types: set[str] = set()
    used_spans: list[tuple[int, int]] = []

    for phrase in broll_phrases:
        if not phrase:
            continue
        norm_phrase = normalize(phrase)
        if norm_phrase not in norm_full:
            continue
        group_type = _broll_type_for_phrase(phrase)
        if group_type in seen_types:
            continue
        idx = norm_full.find(norm_phrase)
        end_idx = idx + len(norm_phrase)
        start = frame_for_phrase(words, full_text, phrase) or frame_for_char_index(words, idx)
        end = start + BROLL_DURATION_FRAMES
        conflict = _overlaps(start, end, occupied)
        if conflict:
            continue
        seen_types.add(group_type)
        used_spans.append((idx, end_idx))
        layout = "greenscreen" if group_type in GREENSCREEN_TYPES else "pip"
        moments.append({
            "type": group_type,
            "start_frame": start,
            "end_frame": end,
            "keyword": phrase,
            "word": phrase,
            "search_query": SEARCH_QUERIES.get(group_type, phrase),
            "layout": layout,
            "source": "script_broll_phrases",
        })
    return moments, seen_types, used_spans


def _step_side_map(script: dict | None) -> dict[int, str]:
    sides: dict[int, str] = {}
    if not script:
        return sides
    for vm in script.get("visual_moments") or []:
        if vm.get("type") != "step":
            continue
        try:
            num = int(str(vm.get("graphic", "0")).strip())
        except ValueError:
            continue
        sides[num] = vm.get("side", "left")
    return sides


def _pair_broll_to_steps(
    moments: list[dict],
    shot_list: dict,
    script: dict | None,
) -> list[dict]:
    """Align B-roll to step windows on the opposite side from the checklist."""
    step_shots = sorted(
        [s for s in shot_list.get("shots", []) if s.get("type") == "STEP_REVEAL"],
        key=lambda s: s["start_frame"],
    )
    if not step_shots:
        return moments

    step_sides = _step_side_map(script)
    paired_steps: set[int] = set()
    result = [dict(m) for m in moments]

    for shot in step_shots:
        step_num = shot.get("params", {}).get("step_number")
        if step_num in paired_steps:
            continue
        step_start = shot["start_frame"]
        step_end = shot["end_frame"]
        checklist_side = step_sides.get(step_num, "left")
        broll_side = "right" if checklist_side == "left" else "left"

        best_idx: int | None = None
        best_dist = 999999
        for i, m in enumerate(result):
            if m.get("step_paired"):
                continue
            if m.get("layout") == "greenscreen":
                continue
            dist = abs(m["start_frame"] - step_start)
            if dist < best_dist and dist <= 120:
                best_dist = dist
                best_idx = i

        if best_idx is not None:
            m = result[best_idx]
            m["start_frame"] = step_start + 8
            m["end_frame"] = min(step_end, m["start_frame"] + BROLL_DURATION_FRAMES)
            m["step_paired"] = step_num
            m["side"] = broll_side
            m["layout"] = "pip"
            paired_steps.add(step_num)

    return result


def detect(transcript: dict, shot_list: dict, script: dict | None = None) -> dict:
    words = transcript.get("words", [])
    occupied = _occupied_ranges(shot_list)
    moments: list[dict] = []
    skipped: list[dict] = []

    if script is None:
        script = shot_list.get("script_metadata")

    full_text = normalize(transcript.get("full_text", ""))

    seeded, seen_types, used_spans = _seed_script_broll_phrases(script, transcript, occupied)
    moments.extend(seeded)

    # Phrase-first: longest keywords first
    all_phrases: list[tuple[str, str]] = []
    for group_type, keywords in KEYWORD_GROUPS.items():
        for kw in sorted(keywords, key=len, reverse=True):
            if " " in kw:
                all_phrases.append((group_type, kw))
    all_phrases.sort(key=lambda x: len(x[1]), reverse=True)

    for group_type, phrase in all_phrases:
        if group_type in seen_types:
            continue
        if phrase not in full_text:
            continue
        idx = full_text.find(phrase)
        end_idx = idx + len(phrase)
        if any(idx < e and end_idx > s for s, e in used_spans):
            continue

        start = frame_for_char_index(words, idx)
        end = start + BROLL_DURATION_FRAMES
        conflict = _overlaps(start, end, occupied)
        if conflict:
            skipped.append({
                "type": group_type,
                "start_frame": start,
                "keyword": phrase,
                "reason": f"conflicts with {conflict}",
            })
            continue

        seen_types.add(group_type)
        used_spans.append((idx, end_idx))
        layout = "greenscreen" if group_type in GREENSCREEN_TYPES else "pip"
        moments.append({
            "type": group_type,
            "start_frame": start,
            "end_frame": end,
            "keyword": phrase,
            "word": phrase,
            "search_query": SEARCH_QUERIES.get(group_type, phrase),
            "layout": layout,
        })

    # Single-word fallback for types not yet matched (min 5 chars, no broad terms)
    for group_type, keywords in KEYWORD_GROUPS.items():
        if group_type in seen_types:
            continue
        single_words = [kw for kw in keywords if " " not in kw and len(kw) >= 5]
        for word_obj in words:
            token = normalize(word_obj.get("word", ""))
            if len(token) < 5:
                continue
            if not any(token == kw for kw in single_words):
                continue

            start = word_obj["start_frame"]
            end = start + BROLL_DURATION_FRAMES
            conflict = _overlaps(start, end, occupied)
            if conflict:
                skipped.append({
                    "type": group_type,
                    "start_frame": start,
                    "keyword": word_obj["word"],
                    "reason": f"conflicts with {conflict}",
                })
                break

            seen_types.add(group_type)
            layout = "greenscreen" if group_type in GREENSCREEN_TYPES else "pip"
            moments.append({
                "type": group_type,
                "start_frame": start,
                "end_frame": end,
                "keyword": word_obj["word"],
                "word": word_obj["word"],
                "search_query": SEARCH_QUERIES.get(group_type, group_type.replace("_", " ")),
                "layout": layout,
            })
            break

    moments.sort(key=lambda m: m["start_frame"])
    moments = _pair_broll_to_steps(moments, shot_list, script)

    # Stagger + rate limit (max 1 per 8 seconds)
    accepted: list[dict] = []
    last_end = -STAGGER_FRAMES
    for m in moments:
        if m["start_frame"] < last_end + STAGGER_FRAMES:
            skipped.append({**m, "reason": "stagger conflict with previous B-roll"})
            continue
        if accepted and m["start_frame"] < accepted[-1]["start_frame"] + RATE_LIMIT_FRAMES:
            skipped.append({**m, "reason": "rate limit (max 1 per 8 seconds)"})
            continue
        accepted.append(m)
        last_end = m["end_frame"]

    return {
        "moments": accepted,
        "skipped": skipped,
        "summary": {
            "detected": len(accepted),
            "skipped": len(skipped),
            "types": [m["type"] for m in accepted],
        },
    }


def save(result: dict, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2))
    return path
