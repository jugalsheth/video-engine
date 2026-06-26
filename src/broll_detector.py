from __future__ import annotations

import json
from pathlib import Path

from src.conflict_helpers import occupied_ranges, overlaps
from src.conflict_rules import (
    composited_layouts,
    hook_composited_ignore_blocking,
    hook_frame_limit,
    load_rules,
)
from src.broll_visual_context import enrich_moment_context
from src.frame_utils import normalize
from src.trigger_utils import resolve_phrase_frame

_rules = load_rules()
BROLL_DURATION_FRAMES = 75
BROLL_DURATION_AI_FRAMES = 105
IMMERSIVE_FLASH_FRAMES = 15
STAGGER_FRAMES = int(_rules.get("broll_stagger_frames", 10))
RATE_LIMIT_FRAMES = int(_rules.get("broll_rate_limit_frames", 240))
HOOK_FRAME_LIMIT = hook_frame_limit()

GREENSCREEN_TYPES = {"data_flow", "terminal", "linkedin", "salary", "growth_chart"}
COMPOSITED_LAYOUTS = composited_layouts()

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

CONFLICT_SHOT_TYPES = {"TITLE_CARD", "CUSTOM_VISUAL"}


def _layout_map(script: dict | None) -> dict[str, str]:
    triggers = (script or {}).get("video_triggers") or {}
    phrases = triggers.get("broll_phrases") or []
    layouts = triggers.get("broll_layouts") or []
    mapping: dict[str, str] = {}
    for i, phrase in enumerate(phrases):
        if phrase and i < len(layouts) and layouts[i]:
            mapping[normalize(phrase)] = str(layouts[i])
    return mapping


def _resolve_layout(
    group_type: str,
    start_frame: int,
    phrase: str,
    script: dict | None,
) -> str:
    phrase_norm = normalize(phrase)
    explicit = _layout_map(script).get(phrase_norm)
    if explicit in COMPOSITED_LAYOUTS or explicit in {"pip", "greenscreen"}:
        return explicit

    if group_type in GREENSCREEN_TYPES:
        if start_frame < HOOK_FRAME_LIMIT and explicit == "immersive_flash":
            return "immersive_flash"
        if explicit == "presenter_cutout":
            return "presenter_cutout"
        return "presenter_on_bg"
    return "pip"


def _duration_frames(layout: str, group_type: str) -> int:
    if layout == "immersive_flash":
        return IMMERSIVE_FLASH_FRAMES
    if layout in COMPOSITED_LAYOUTS or group_type in GREENSCREEN_TYPES:
        return BROLL_DURATION_AI_FRAMES
    return BROLL_DURATION_FRAMES


def _conflict_ignore(layout: str, start_frame: int) -> set[str] | None:
    if layout in COMPOSITED_LAYOUTS and start_frame < HOOK_FRAME_LIMIT:
        return hook_composited_ignore_blocking()
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
    # Unknown phrases: keep type generic but caller should use phrase as search_query
    return "custom"


def _seed_script_broll_phrases(
    script: dict | None,
    transcript: dict,
    occupied: list[tuple],
    skipped: list[dict],
) -> tuple[list[dict], set[str], list[tuple[int, int]]]:
    if not script:
        return [], set(), []

    triggers = script.get("video_triggers") or {}
    broll_phrases = triggers.get("broll_phrases") or []
    words = transcript.get("words", [])
    full_text = transcript.get("full_text", "")
    norm_full = normalize(full_text)
    moments: list[dict] = []
    seen_phrases: set[str] = set()
    used_spans: list[tuple[int, int]] = []

    for phrase in broll_phrases:
        if not phrase:
            continue
        norm_phrase = normalize(phrase)
        if norm_phrase in seen_phrases:
            continue
        start, match_method = resolve_phrase_frame(words, full_text, phrase)
        if start is None:
            skipped.append({
                "keyword": phrase,
                "reason": "phrase not in transcript",
                "source": "script_broll_phrases",
            })
            continue
        idx = norm_full.find(norm_phrase)
        if idx == -1:
            idx = 0
        end_idx = idx + len(norm_phrase)
        group_type = _broll_type_for_phrase(phrase)
        layout = _resolve_layout(group_type, start, phrase, script)
        duration = _duration_frames(layout, group_type)
        end = start + duration
        conflict = overlaps(
            start,
            end,
            occupied,
            ignore_labels=_conflict_ignore(layout, start),
            with_labels=True,
        )
        if conflict:
            skipped.append({
                "keyword": phrase,
                "start_frame": start,
                "reason": f"conflicts with {conflict}",
                "source": "script_broll_phrases",
            })
            continue
        seen_phrases.add(norm_phrase)
        used_spans.append((idx, end_idx))
        moments.append({
            "type": group_type,
            "start_frame": start,
            "end_frame": end,
            "keyword": phrase,
            "word": phrase,
            "search_query": SEARCH_QUERIES.get(group_type, phrase),
            "layout": layout,
            "source": "script_broll_phrases",
            "match_method": match_method,
        })
    return moments, seen_phrases, used_spans


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
            if m.get("layout") in {"greenscreen", *COMPOSITED_LAYOUTS}:
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
    occupied = occupied_ranges(shot_list, moment_type="broll", with_labels=True)
    moments: list[dict] = []
    skipped: list[dict] = []

    if script is None:
        script = shot_list.get("script_metadata")

    full_text = transcript.get("full_text", "")

    seeded, seen_phrases, used_spans = _seed_script_broll_phrases(
        script, transcript, occupied, skipped,
    )
    moments.extend(seeded)

    # Phrase-first: longest keywords first
    all_phrases: list[tuple[str, str]] = []
    for group_type, keywords in KEYWORD_GROUPS.items():
        for kw in sorted(keywords, key=len, reverse=True):
            if " " in kw:
                all_phrases.append((group_type, kw))
    all_phrases.sort(key=lambda x: len(x[1]), reverse=True)

    for group_type, phrase in all_phrases:
        norm_phrase = normalize(phrase)
        if norm_phrase in seen_phrases:
            continue
        start, _match_method = resolve_phrase_frame(words, full_text, phrase)
        if start is None:
            continue
        norm_full = normalize(full_text)
        idx = norm_full.find(norm_phrase)
        if idx == -1:
            continue
        end_idx = idx + len(norm_phrase)
        if any(idx < e and end_idx > s for s, e in used_spans):
            continue

        layout = _resolve_layout(group_type, start, phrase, script)
        duration = _duration_frames(layout, group_type)
        end = start + duration
        conflict = overlaps(
            start,
            end,
            occupied,
            ignore_labels=_conflict_ignore(layout, start),
            with_labels=True,
        )
        if conflict:
            skipped.append({
                "type": group_type,
                "start_frame": start,
                "keyword": phrase,
                "reason": f"conflicts with {conflict}",
            })
            continue

        seen_phrases.add(norm_phrase)
        used_spans.append((idx, end_idx))
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
    seen_types = {m["type"] for m in moments}
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
            layout = _resolve_layout(group_type, start, word_obj["word"], script)
            duration = _duration_frames(layout, group_type)
            end = start + duration
            conflict = overlaps(
                start,
                end,
                occupied,
                ignore_labels=_conflict_ignore(layout, start),
                with_labels=True,
            )
            if conflict:
                skipped.append({
                    "type": group_type,
                    "start_frame": start,
                    "keyword": word_obj["word"],
                    "reason": f"conflicts with {conflict}",
                })
                break

            seen_types.add(group_type)
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

    for i, m in enumerate(moments):
        moments[i] = enrich_moment_context(m, transcript, script)
        brief_src = (script or {}).get("video_triggers") or {}
        descs = brief_src.get("broll_image_descriptions") or []
        phrases = brief_src.get("broll_phrases") or []
        kw = normalize(m.get("keyword", ""))
        for j, phrase in enumerate(phrases):
            if phrase and (normalize(phrase) in kw or kw in normalize(phrase)):
                if j < len(descs) and descs[j]:
                    moments[i]["visual_brief"] = descs[j]
                break

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
