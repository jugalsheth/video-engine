from __future__ import annotations

import os


def _flag(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).lower() in ("1", "true", "yes")


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


def broll_mode() -> str:
    if zero_cost_mode():
        return "svg"
    return os.getenv("BROLL_MODE", "auto").lower()


def whisper_model() -> str:
    return os.getenv("WHISPER_MODEL", "small" if zero_cost_mode() else "base")


def jump_cut_min_silence() -> float:
    return float(os.getenv("JUMP_CUT_MIN_SILENCE", "0.15"))


def jump_cut_max_remove_ratio() -> float:
    return float(os.getenv("JUMP_CUT_MAX_REMOVE_RATIO", "0.35"))


def voice_enhance_enabled() -> bool:
    return _flag("VOICE_ENHANCE", "true")


def voice_denoise_strength() -> int:
    """afftdn noise floor in dB; -20 light, -25 default, -30 aggressive."""
    return int(os.getenv("VOICE_DENOISE_STRENGTH", "-25"))
