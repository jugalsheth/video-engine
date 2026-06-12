"""Resolve per-script Remotion render props from edit_template and brand config."""

from __future__ import annotations

TEMPLATE_RENDER_PROFILES = {
    "THREE_STEP_HOT_TAKE": {
        "graphicsScale": 1.8,
        "captionVerticalPosition": 75,
        "zoomIntensity": 1.2,
        "captionStyle": "viral",
    },
    "CONFESSION_STAT": {
        "graphicsScale": 1.75,
        "captionVerticalPosition": 75,
        "zoomIntensity": 1.18,
        "captionStyle": "viral",
    },
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
    }

    if script:
        triggers = script.get("video_triggers") or {}
        props["energyWords"] = triggers.get("energy_words") or ["right", "truth"]

    return props
