from __future__ import annotations

import json
import os
from pathlib import Path

from src.project_paths import project_dir


def _flag(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).lower() in ("1", "true", "yes")


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


def zero_cost_mode() -> bool:
    return _flag("ZERO_COST_MODE", "true")


def use_design_agent() -> bool:
    if zero_cost_mode():
        return False
    return _flag("USE_DESIGN_AGENT", "false")


def jump_cuts_enabled() -> bool:
    return _flag("JUMP_CUTS", "true")


def global_fx_enabled() -> bool:
    return _flag("GLOBAL_FX", "false")


def skip_stock_fetch() -> bool:
    if zero_cost_mode():
        return True
    return _flag("SKIP_STOCK_FETCH", "false")


def fal_api_key() -> str:
    return os.getenv("FAL_KEY", "").strip()


def ai_images_enabled() -> bool:
    if not fal_api_key():
        return False
    if zero_cost_mode() and not _flag("AI_IMAGES", "false"):
        return False
    return _flag("AI_IMAGES", "false") or broll_mode() == "ai"


def ai_image_model() -> str:
    return os.getenv("AI_IMAGE_MODEL", "flux-schnell").lower()


def ai_image_max_per_video() -> int:
    return int(os.getenv("AI_IMAGE_MAX_PER_VIDEO", "8"))


def ai_cutout_max_per_video() -> int:
    return int(os.getenv("AI_CUTOUT_MAX_PER_VIDEO", "1"))


def ai_cutout_model() -> str:
    return os.getenv("AI_CUTOUT_MODEL", "light").lower()


def ai_cost_ceiling_usd() -> float:
    return float(os.getenv("AI_COST_CEILING_USD", "0.05"))


def broll_mode() -> str:
    mode = os.getenv("BROLL_MODE", "auto").lower()
    if zero_cost_mode():
        if _flag("AI_IMAGES", "false") or mode == "ai":
            return "ai" if mode == "ai" or _flag("AI_IMAGES", "false") else "svg"
        return "svg"
    return mode


def whisper_model() -> str:
    return os.getenv("WHISPER_MODEL", "small" if zero_cost_mode() else "base")


def jump_cut_min_silence() -> float:
    return float(os.getenv("JUMP_CUT_MIN_SILENCE", "0.15"))


def jump_cut_max_remove_ratio() -> float:
    return float(os.getenv("JUMP_CUT_MAX_REMOVE_RATIO", "0.35"))


def step_sfx_lag_frames() -> int:
    """Delay step punch/swoosh SFX to align with spoken number (Whisper leads slightly)."""
    return int(os.getenv("STEP_SFX_LAG_FRAMES", "5"))


def voice_enhance_enabled() -> bool:
    return _flag("VOICE_ENHANCE", "true")


def voice_denoise_strength() -> int:
    """afftdn noise floor in dB; -20 light, -25 default, -30 aggressive."""
    return int(os.getenv("VOICE_DENOISE_STRENGTH", "-25"))


def _load_project_config_file(project_id: str) -> dict:
    path = project_dir(project_id) / "project_config.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def resolve_config(project_id: str | None = None) -> dict:
    """
    Merge env defaults with per-project pipeline block from project_config.json.
  Keys: jump_cuts, broll_mode, voice_enhance, ai_images, caption_vertical_position
    """
    cfg: dict = {
        "jump_cuts": jump_cuts_enabled(),
        "broll_mode": broll_mode(),
        "voice_enhance": voice_enhance_enabled(),
        "ai_images": ai_images_enabled(),
        "global_fx": global_fx_enabled(),
        "whisper_model": whisper_model(),
        "ai_cost_ceiling_usd": ai_cost_ceiling_usd(),
        "ai_image_max_per_video": ai_image_max_per_video(),
        "caption_vertical_position": int(_env("CAPTION_VERTICAL_POSITION", "75")),
    }
    if not project_id:
        return cfg

    project_cfg = _load_project_config_file(project_id)
    pipeline = project_cfg.get("pipeline") or {}
    for key, value in pipeline.items():
        if key in cfg:
            cfg[key] = value
    return cfg
