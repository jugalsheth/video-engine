from __future__ import annotations

import json
import re
from pathlib import Path

from src.frame_utils import frame_for_char_index, frame_for_phrase, normalize
from src.rules_loader import load_global_fx_map
from src.pipeline_config import global_fx_enabled

MAX_GLITCH_BURST = 1
MAX_NOTIFICATION_TOAST = 2

DEFAULT_DURATIONS = {
    "glitch_burst": 8,
    "freeze_stamp": 16,
    "screen_shake": 10,
    "notification_toast": 45,
    "vhs_filter": 0,  # segment-based; end_frame computed
    "split_wipe": 12,
}

BEFORE_PHRASES = {"the old way", "before", "used to", "back then"}
AFTER_PHRASES = {"the new way", "now", "after", "these days"}


def _load_map() -> dict:
    return load_global_fx_map()


def _phrase_in_text(phrase: str, full_text: str) -> tuple[int, int] | None:
    norm_phrase = normalize(phrase)
    norm_full = normalize(full_text)
    if norm_phrase not in norm_full:
        return None
    idx = norm_full.find(norm_phrase)
    return idx, idx + len(norm_phrase)


def _detect_phrase_moments(
    fx_type: str,
    phrases: list[str],
    transcript: dict,
    full_text: str,
    max_count: int,
    *,
    extra_fields=None,
) -> list[dict]:
    words = transcript.get("words", [])
    moments: list[dict] = []
    used_spans: list[tuple[int, int]] = []

    for phrase in sorted(phrases, key=len, reverse=True):
        if len(moments) >= max_count:
            break
        span = _phrase_in_text(phrase, full_text)
        if span is None:
            continue
        idx, end_idx = span
        if any(idx < e and end_idx > s for s, e in used_spans):
            continue
        start = frame_for_phrase(words, transcript.get("full_text", ""), phrase)
        if start is None:
            start = frame_for_char_index(words, idx)
        moment: dict = {
            "type": fx_type,
            "start_frame": start,
            "duration_frames": DEFAULT_DURATIONS[fx_type],
            "source": "trigger_phrase",
            "trigger_phrase": phrase,
        }
        if extra_fields:
            extra = extra_fields(phrase)
            if extra:
                moment.update(extra)
        moments.append(moment)
        used_spans.append((idx, end_idx))

    return moments


def _freeze_stamps_from_stats(shot_list: dict) -> list[dict]:
    moments: list[dict] = []
    for shot in shot_list.get("shots", []):
        if shot.get("type") != "STAT_CALLOUT":
            continue
        params = shot.get("params", {})
        number = params.get("number", "")
        stamp_text = str(number) if number else "0"
        moments.append({
            "type": "freeze_stamp",
            "start_frame": shot["start_frame"],
            "duration_frames": DEFAULT_DURATIONS["freeze_stamp"],
            "stamp_text": stamp_text,
            "source": "stat_phrase",
            "trigger_phrase": stamp_text,
        })
    return moments


def _screen_shakes_from_beats(beats: dict | None, render_props: dict | None) -> list[dict]:
    if not beats:
        return []
    intensity = (render_props or {}).get("shakeIntensity", 2.5)
    crust = beats.get("crust_start")
    if crust is None:
        return []
    return [{
        "type": "screen_shake",
        "start_frame": int(crust),
        "duration_frames": DEFAULT_DURATIONS["screen_shake"],
        "intensity": float(intensity),
        "source": "crust_beat",
    }]


def _vhs_segments(
    transcript: dict,
    script: dict | None,
    full_text: str,
) -> list[dict]:
    """Detect before/after segment ranges for VHS filter + split wipe."""
    segments: list[dict] = []
    words = transcript.get("words", [])
    norm_full = normalize(full_text)

    visual_moments = (script or {}).get("visual_moments") or []
    for vm in visual_moments:
        vm_type = (vm.get("type") or "").lower()
        phrase = vm.get("at_phrase") or vm.get("phrase") or ""
        if not phrase:
            continue
        start = frame_for_phrase(words, transcript.get("full_text", ""), phrase)
        if start is None:
            continue
        if vm_type in ("before", "before_segment", "old_way"):
            segments.append({"kind": "before", "start_frame": start, "phrase": phrase})
        elif vm_type in ("after", "after_segment", "new_way"):
            segments.append({"kind": "after", "start_frame": start, "phrase": phrase})

    fx_map = _load_map()
    before_phrases = fx_map.get("vhs_before_phrases", list(BEFORE_PHRASES))
    after_phrases = fx_map.get("vhs_after_phrases", list(AFTER_PHRASES))

    for phrase in before_phrases:
        span = _phrase_in_text(phrase, full_text)
        if span is None:
            continue
        start = frame_for_phrase(words, transcript.get("full_text", ""), phrase)
        if start is None:
            start = frame_for_char_index(words, span[0])
        if not any(s["kind"] == "before" and abs(s["start_frame"] - start) < 30 for s in segments):
            segments.append({"kind": "before", "start_frame": start, "phrase": phrase})

    for phrase in after_phrases:
        span = _phrase_in_text(phrase, full_text)
        if span is None:
            continue
        start = frame_for_phrase(words, transcript.get("full_text", ""), phrase)
        if start is None:
            start = frame_for_char_index(words, span[0])
        if not any(s["kind"] == "after" and abs(s["start_frame"] - start) < 30 for s in segments):
            segments.append({"kind": "after", "start_frame": start, "phrase": phrase})

    before_segs = sorted([s for s in segments if s["kind"] == "before"], key=lambda x: x["start_frame"])
    after_segs = sorted([s for s in segments if s["kind"] == "after"], key=lambda x: x["start_frame"])

    moments: list[dict] = []
    total_frames = transcript.get("total_frames", 300)

    for b in before_segs:
        matching_after = next((a for a in after_segs if a["start_frame"] > b["start_frame"]), None)
        end_frame = matching_after["start_frame"] if matching_after else min(b["start_frame"] + 90, total_frames)
        if end_frame <= b["start_frame"]:
            continue
        moments.append({
            "type": "vhs_filter",
            "start_frame": b["start_frame"],
            "duration_frames": end_frame - b["start_frame"],
            "end_frame": end_frame,
            "source": "before_segment",
            "trigger_phrase": b["phrase"],
        })

    for i, b in enumerate(before_segs):
        matching_after = next((a for a in after_segs if a["start_frame"] > b["start_frame"]), None)
        if not matching_after:
            continue
        wipe_start = matching_after["start_frame"] - DEFAULT_DURATIONS["split_wipe"] // 2
        if wipe_start < b["start_frame"]:
            wipe_start = matching_after["start_frame"]
        moments.append({
            "type": "split_wipe",
            "start_frame": max(0, wipe_start),
            "duration_frames": DEFAULT_DURATIONS["split_wipe"],
            "source": "segment_transition",
            "trigger_phrase": f"{b['phrase']}->{matching_after['phrase']}",
        })
        break

    return moments


def detect(
    transcript: dict,
    shot_list: dict,
    beats: dict | None = None,
    script: dict | None = None,
    render_props: dict | None = None,
) -> dict:
    if not global_fx_enabled():
        return {
            "moments": [],
            "skipped": [],
            "summary": {"detected": 0, "skipped": 0, "types": []},
        }

    if script is None:
        script = shot_list.get("script_metadata")

    fx_map = _load_map()
    full_text = transcript.get("full_text", "")
    norm_full = normalize(full_text)
    moments: list[dict] = []
    skipped: list[dict] = []

    toast_mapping = fx_map.get("toast_text_mapping", {})
    icon_mapping = fx_map.get("toast_icon_mapping", {})

    def toast_extra(phrase: str) -> dict:
        norm = normalize(phrase)
        text = toast_mapping.get(norm, "12 new")
        icon = icon_mapping.get(norm, "slack")
        return {"toast_text": text, "toast_icon": icon, "side": "right"}

    toast_enabled = (render_props or {}).get("toastEnabled", True)
    vhs_enabled = (render_props or {}).get("vhsEnabled", False)

    glitch_phrases = fx_map.get("glitch_burst", [])
    glitch_intensity = (render_props or {}).get("glitchIntensity", 0.6)
    moments.extend(_detect_phrase_moments(
        "glitch_burst",
        glitch_phrases,
        transcript,
        norm_full,
        MAX_GLITCH_BURST,
        extra_fields=lambda p: {"intensity": float(glitch_intensity), "trigger_phrase": p},
    ))

    if toast_enabled:
        toast_phrases = fx_map.get("notification_toast", [])
        moments.extend(_detect_phrase_moments(
            "notification_toast",
            toast_phrases,
            transcript,
            norm_full,
            MAX_NOTIFICATION_TOAST,
            extra_fields=toast_extra,
        ))

    if (render_props or {}).get("freezeStampEnabled", False):
        moments.extend(_freeze_stamps_from_stats(shot_list))
    moments.extend(_screen_shakes_from_beats(beats, render_props))

    if vhs_enabled:
        moments.extend(_vhs_segments(transcript, script, full_text))

    # Seed explicit global_fx_phrases from script
    triggers = (script or {}).get("video_triggers") or {}
    for entry in triggers.get("global_fx_phrases") or []:
        if isinstance(entry, str):
            fx_type, phrase = "glitch_burst", entry
        else:
            fx_type = entry.get("type", "glitch_burst")
            phrase = entry.get("phrase", "")
        if not phrase or fx_type not in DEFAULT_DURATIONS:
            continue
        span = _phrase_in_text(phrase, full_text)
        if span is None:
            skipped.append({"type": fx_type, "trigger_phrase": phrase, "reason": "phrase not in transcript"})
            continue
        words = transcript.get("words", [])
        start = frame_for_phrase(words, full_text, phrase) or frame_for_char_index(words, span[0])
        if any(m["type"] == fx_type and m["start_frame"] == start for m in moments):
            continue
        moment = {
            "type": fx_type,
            "start_frame": start,
            "duration_frames": DEFAULT_DURATIONS.get(fx_type, 8),
            "source": "script_seed",
            "trigger_phrase": phrase,
        }
        if fx_type == "glitch_burst":
            moment["intensity"] = float(glitch_intensity)
        if fx_type == "notification_toast":
            moment.update(toast_extra(phrase))
        moments.append(moment)

    # Block vhs + glitch at same frame (pick glitch, drop vhs)
    glitch_frames = {
        m["start_frame"]
        for m in moments
        if m["type"] == "glitch_burst"
    }
    filtered: list[dict] = []
    for m in moments:
        if m["type"] == "vhs_filter":
            overlaps_glitch = any(
                abs(m["start_frame"] - gf) < m.get("duration_frames", 30)
                for gf in glitch_frames
            )
            if overlaps_glitch:
                skipped.append({**m, "reason": "competes with glitch_burst"})
                continue
        filtered.append(m)

    filtered.sort(key=lambda m: m["start_frame"])

    return {
        "moments": filtered,
        "skipped": skipped,
        "summary": {
            "detected": len(filtered),
            "skipped": len(skipped),
            "types": list(dict.fromkeys(m["type"] for m in filtered)),
        },
    }


def save(result: dict, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2))
    return path
