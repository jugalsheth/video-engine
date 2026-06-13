from __future__ import annotations

import json
import re
from pathlib import Path

from src.frame_utils import frame_for_char_index, frame_for_phrase, normalize
from src.rules_loader import load_logo_map
from src.shot_planner import _flex_frame

LOGO_DURATION_FRAMES = 36  # 1.2s
RATE_LIMIT_FRAMES = 54  # 1.8s
TOOL_BURST_WINDOW_FRAMES = 150  # allow tight spacing when listing tools
MAX_LOGO_MOMENTS = 6
MIN_TOKEN_LEN = 3

CONFLICT_SHOT_TYPES = {"TITLE_CARD", "CUSTOM_VISUAL"}
TITLE_END_BUFFER_FRAMES = 12

# Map broll_phrases / spoken mishears → brand_id
BROLL_BRAND_HINTS: dict[str, str] = {
    "openai api": "openai",
    "open ai api": "openai",
    "openai": "openai",
    "langchain": "langchain",
    "llamaindex": "llamaindex",
    "llama index": "llamaindex",
    "meta": "meta",
    "github copilot": "githubcopilot",
    "cursor": "cursor",
    "claude": "anthropic",
    "chatgpt": "openai",
    "kafka": "apachekafka",
    "databricks": "databricks",
}


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


def _tokenize(text: str) -> str:
    return normalize(text)


def _collapse(text: str) -> str:
    return _tokenize(text).replace(" ", "")


def _build_alias_index(logo_map: dict) -> list[tuple[str, str, str]]:
    """Return (alias, brand_id, file) sorted longest alias first."""
    entries: list[tuple[str, str, str]] = []
    for brand_id, meta in logo_map.items():
        file_name = meta["file"]
        for alias in meta.get("aliases", [brand_id]):
            norm = _tokenize(alias)
            if len(norm) >= MIN_TOKEN_LEN or " " in norm:
                entries.append((norm, brand_id, file_name))
    entries.sort(key=lambda x: len(x[0]), reverse=True)
    return entries


def _find_phrase_in_text(full_text: str, alias: str) -> int | None:
    norm_full = _tokenize(full_text)
    norm_alias = _tokenize(alias)
    idx = norm_full.find(norm_alias)
    if idx != -1:
        return idx
    collapsed_full = _collapse(full_text)
    collapsed_alias = _collapse(alias)
    if len(collapsed_alias) >= MIN_TOKEN_LEN:
        cidx = collapsed_full.find(collapsed_alias)
        if cidx != -1:
            return cidx
    return None


def _find_alias_word_window(words: list, alias: str) -> int | None:
    """Match alias across split Whisper tokens (e.g. open + ai → openai)."""
    collapsed_alias = _collapse(alias)
    if len(collapsed_alias) < MIN_TOKEN_LEN:
        return None
    max_window = min(6, len(collapsed_alias) + 2)
    for i in range(len(words)):
        chunk = ""
        for j in range(i, min(i + max_window, len(words))):
            chunk += _collapse(words[j].get("word", ""))
            if collapsed_alias in chunk:
                return words[i]["start_frame"]
            if len(chunk) > len(collapsed_alias) + 8:
                break
    return None


def _resolve_start_frame(words: list, full_text: str, phrase: str) -> int | None:
    frame = _flex_frame(words, full_text, phrase)
    if frame is not None:
        return frame
    frame = frame_for_phrase(words, full_text, phrase)
    if frame is not None:
        return frame
    idx = _find_phrase_in_text(full_text, phrase)
    if idx is not None:
        return frame_for_char_index(words, idx)
    return _find_alias_word_window(words, phrase)


def _append_moment(
    moments: list[dict],
    used_brands: set[str],
    used_spans: list[tuple[int, int]],
    occupied: list[tuple[int, int]],
    side_toggle: int,
    brand_id: str,
    logo_map: dict,
    start: int,
    keyword: str,
    full_text: str,
) -> int:
    meta = logo_map.get(brand_id)
    if not meta or brand_id in used_brands:
        return side_toggle
    end = start + LOGO_DURATION_FRAMES
    if _overlaps(start, end, occupied):
        return side_toggle
    idx = _find_phrase_in_text(full_text, keyword)
    span = (idx or 0, (idx or 0) + len(_tokenize(keyword)))
    if any(span[0] < e and span[1] > s for s, e in used_spans):
        return side_toggle
    side = "left" if side_toggle % 2 == 0 else "right"
    moments.append({
        "type": "logo_pop",
        "brand": brand_id,
        "logo_file": meta["file"],
        "label": meta.get("label", brand_id.title()),
        "start_frame": start,
        "end_frame": end,
        "keyword": keyword,
        "side": side,
    })
    used_brands.add(brand_id)
    used_spans.append(span)
    return side_toggle + 1


def _seed_script_logos(
    script: dict | None,
    transcript: dict,
    logo_map: dict,
    occupied: list[tuple[int, int]],
) -> tuple[list[dict], set[str], int, list[tuple[int, int]]]:
    if not script:
        return [], set(), 0, []

    triggers = script.get("video_triggers") or {}
    logo_phrases = list(triggers.get("logo_phrases") or [])
    broll_phrases = triggers.get("broll_phrases") or []
    for phrase in broll_phrases:
        if isinstance(phrase, str):
            hint = BROLL_BRAND_HINTS.get(_tokenize(phrase), "")
            if hint:
                logo_phrases.append({"phrase": phrase, "brand": hint})

    words = transcript.get("words", [])
    full_text = transcript.get("full_text", "")
    moments: list[dict] = []
    used_brands: set[str] = set()
    used_spans: list[tuple[int, int]] = []
    side_toggle = 0

    for entry in logo_phrases:
        if isinstance(entry, str):
            phrase, brand_id = entry, None
        else:
            phrase = entry.get("phrase", "")
            brand_id = entry.get("brand", "")
        if not phrase:
            continue
        brand_id = brand_id or BROLL_BRAND_HINTS.get(_tokenize(phrase), phrase.split()[0].lower())
        if brand_id not in logo_map:
            continue
        start = _resolve_start_frame(words, full_text, phrase)
        if start is None:
            continue
        side_toggle = _append_moment(
            moments, used_brands, used_spans, occupied, side_toggle,
            brand_id, logo_map, start, phrase, full_text,
        )

    return moments, used_brands, side_toggle, used_spans


def detect(transcript: dict, shot_list: dict, script: dict | None = None) -> dict:
    logo_map = load_logo_map()
    if not logo_map:
        return {
            "moments": [],
            "skipped": [],
            "summary": {"detected": 0, "skipped": 0, "brands": []},
        }

    words = transcript.get("words", [])
    full_text = transcript.get("full_text", "")
    occupied = _occupied_ranges(shot_list)

    if script is None:
        script = shot_list.get("script_metadata")

    alias_index = _build_alias_index(logo_map)
    moments: list[dict] = []
    skipped: list[dict] = []
    used_brands: set[str] = set()
    used_spans: list[tuple[int, int]] = []

    seeded, seeded_brands, side_toggle, used_spans = _seed_script_logos(
        script, transcript, logo_map, occupied
    )
    moments.extend(seeded)
    used_brands |= seeded_brands

    for alias, brand_id, logo_file in alias_index:
        if brand_id in used_brands:
            continue
        start = _resolve_start_frame(words, full_text, alias)
        if start is None:
            continue
        idx = _find_phrase_in_text(full_text, alias)
        end_idx = (idx or 0) + len(_tokenize(alias))
        if any((idx or 0) < e and end_idx > s for s, e in used_spans):
            continue

        end = start + LOGO_DURATION_FRAMES
        if _overlaps(start, end, occupied):
            skipped.append({
                "brand": brand_id,
                "start_frame": start,
                "keyword": alias,
                "reason": "title conflict",
            })
            continue

        side = "left" if side_toggle % 2 == 0 else "right"
        side_toggle += 1
        meta = logo_map.get(brand_id, {})
        moments.append({
            "type": "logo_pop",
            "brand": brand_id,
            "logo_file": logo_file,
            "label": meta.get("label", brand_id.replace("_", " ").title()),
            "start_frame": start,
            "end_frame": end,
            "keyword": alias,
            "side": side,
        })
        used_brands.add(brand_id)
        used_spans.append(((idx or 0), end_idx))

    moments.sort(key=lambda m: m["start_frame"])

    burst_frames: set[int] = set()
    for m in moments:
        neighbors = [
            o
            for o in moments
            if abs(o["start_frame"] - m["start_frame"]) <= TOOL_BURST_WINDOW_FRAMES
        ]
        if len(neighbors) >= 3:
            burst_frames.update(o["start_frame"] for o in neighbors)

    accepted: list[dict] = []
    last_start = -RATE_LIMIT_FRAMES
    for m in moments:
        if len(accepted) >= MAX_LOGO_MOMENTS:
            skipped.append({**m, "reason": "max logos cap"})
            continue
        if m["start_frame"] not in burst_frames and m["start_frame"] < last_start + RATE_LIMIT_FRAMES:
            skipped.append({**m, "reason": "rate limit"})
            continue
        accepted.append(m)
        last_start = m["start_frame"]

    return {
        "moments": accepted,
        "skipped": skipped,
        "summary": {
            "detected": len(accepted),
            "skipped": len(skipped),
            "brands": [m["brand"] for m in accepted],
        },
    }


def save(result: dict, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2))
    return path
