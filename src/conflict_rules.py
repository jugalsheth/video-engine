from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

ENGINE_ROOT = Path(__file__).resolve().parent.parent
RULES_PATH = ENGINE_ROOT / "config" / "conflict_rules.json"

_DEFAULTS = {
    "title_buffer_frames": 12,
    "step_window_buffer_frames": 60,
    "step_beat_fallback_duration_frames": 75,
    "hook_frame_limit": 90,
    "broll_stagger_frames": 10,
    "broll_rate_limit_frames": 240,
    "composited_layouts": ["presenter_on_bg", "presenter_cutout", "immersive_flash"],
    "hook_composited_ignore_blocking": ["TITLE_CARD", "STAT_CALLOUT"],
    "blocking_shot_types": {
        "broll": ["TITLE_CARD", "CUSTOM_VISUAL"],
        "fun": ["TITLE_CARD", "CUSTOM_VISUAL"],
        "role": ["TITLE_CARD", "CUSTOM_VISUAL"],
        "logo": ["TITLE_CARD", "CUSTOM_VISUAL"],
        "social": ["TITLE_CARD", "CUSTOM_VISUAL"],
    },
    "step_window_moment_types": ["broll", "fun", "role", "social"],
    "broll_overlap_dedup": True,
    "broll_max_per_step": 1,
    "toast_blocks_pip_broll_only": True,
}


@lru_cache(maxsize=1)
def load_rules() -> dict:
    if RULES_PATH.exists():
        data = json.loads(RULES_PATH.read_text(encoding="utf-8"))
        merged = dict(_DEFAULTS)
        merged.update(data)
        return merged
    return dict(_DEFAULTS)


def title_buffer_frames() -> int:
    return int(load_rules().get("title_buffer_frames", 12))


def step_window_buffer_frames() -> int:
    return int(load_rules().get("step_window_buffer_frames", 60))


def blocking_types(moment_type: str = "broll") -> set[str]:
    rules = load_rules()
    types = rules.get("blocking_shot_types", {})
    if isinstance(types, dict):
        return set(types.get(moment_type, types.get("broll", ["TITLE_CARD", "CUSTOM_VISUAL"])))
    return {"TITLE_CARD", "CUSTOM_VISUAL"}


def composited_layouts() -> set[str]:
    return set(load_rules().get("composited_layouts", []))


def hook_composited_ignore_blocking() -> set[str]:
    return set(load_rules().get("hook_composited_ignore_blocking", []))


def hook_frame_limit() -> int:
    return int(load_rules().get("hook_frame_limit", 90))
