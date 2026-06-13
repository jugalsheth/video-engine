"""Resolve per-script Remotion render props from edit_template and brand config."""

from __future__ import annotations

TEMPLATE_RENDER_PROFILES = {
    "THREE_STEP_HOT_TAKE": {
        "graphicsScale": 1.8,
        "captionVerticalPosition": 75,
        "zoomIntensity": 1.2,
        "captionStyle": "viral",
        "glitchIntensity": 0.7,
        "shakeIntensity": 2.5,
        "tickerEnabled": True,
        "toastEnabled": True,
        "vhsEnabled": True,
        "freezeStampEnabled": False,
    },
    "CONFESSION_STAT": {
        "graphicsScale": 1.75,
        "captionVerticalPosition": 75,
        "zoomIntensity": 1.18,
        "captionStyle": "viral",
        "glitchIntensity": 0.8,
        "shakeIntensity": 2,
        "tickerEnabled": True,
        "toastEnabled": False,
        "vhsEnabled": True,
        "freezeStampEnabled": False,
    },
}

DEFAULT_FX_PROPS = {
    "glitchIntensity": 0.5,
    "shakeIntensity": 2,
    "tickerEnabled": True,
    "toastEnabled": True,
    "vhsEnabled": False,
    "freezeStampEnabled": False,
}


def resolve_render_props(script: dict | None, brand_config: dict | None = None) -> dict:
    brand = brand_config or {}
    template_id = (script or {}).get("edit_template") or "THREE_STEP_HOT_TAKE"
    profile = TEMPLATE_RENDER_PROFILES.get(template_id, TEMPLATE_RENDER_PROFILES["THREE_STEP_HOT_TAKE"])

    props = {
        "titleVerticalPosition": brand.get("titleVerticalPosition", 15),
        "captionVerticalPosition": profile["captionVerticalPosition"],
        "captionStyle": profile["captionStyle"],
        "zoomIntensity": profile["zoomIntensity"],
        "graphicsScale": profile["graphicsScale"],
        "statCalloutSide": brand.get("statCalloutSide", "right"),
        "glitchIntensity": profile.get("glitchIntensity", DEFAULT_FX_PROPS["glitchIntensity"]),
        "shakeIntensity": profile.get("shakeIntensity", DEFAULT_FX_PROPS["shakeIntensity"]),
        "tickerEnabled": profile.get("tickerEnabled", DEFAULT_FX_PROPS["tickerEnabled"]),
        "toastEnabled": profile.get("toastEnabled", DEFAULT_FX_PROPS["toastEnabled"]),
        "vhsEnabled": profile.get("vhsEnabled", DEFAULT_FX_PROPS["vhsEnabled"]),
        "freezeStampEnabled": profile.get("freezeStampEnabled", DEFAULT_FX_PROPS["freezeStampEnabled"]),
    }

    if script:
        triggers = script.get("video_triggers") or {}
        props["energyWords"] = triggers.get("energy_words") or ["right", "truth"]

    return props
