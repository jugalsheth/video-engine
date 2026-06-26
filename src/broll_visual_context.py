from __future__ import annotations

import json
import re
from pathlib import Path

from src.frame_utils import normalize

ENGINE_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_PATH = ENGINE_ROOT / "rules" / "broll_visual_templates.json"
BRAND_CONFIG_PATH = ENGINE_ROOT / "rules" / "brand_config.json"

HARD_NEGATIVES = (
    "Avoid: people, faces, suits, businessmen, stock photo humans, server room aisles, "
    "legible text, watermarks, logos, cluttered foreground."
)

_STYLE_ANCHOR = (
    "Style: dark cinematic vertical 9:16, teal #00D4FF and amber #C9923A accents, "
    "tech education reel, high contrast."
)


def _load_templates() -> dict[str, str]:
    if not TEMPLATES_PATH.exists():
        return {}
    try:
        return json.loads(TEMPLATES_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _load_brand() -> dict:
    if not BRAND_CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(BRAND_CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def template_for_phrase(phrase: str) -> str | None:
    templates = _load_templates()
    norm = normalize(phrase)
    if norm in templates:
        return templates[norm]
    for key, value in templates.items():
        if key in norm or norm in key:
            return value
    return None


def transcript_window(words: list, start_frame: int, *, window_words: int = 18) -> str:
    if not words:
        return ""
    anchor_idx = 0
    for i, w in enumerate(words):
        if w.get("start_frame", 0) >= start_frame:
            anchor_idx = i
            break
    else:
        anchor_idx = len(words) - 1
    lo = max(0, anchor_idx - window_words // 2)
    hi = min(len(words), anchor_idx + window_words // 2)
    snippet = " ".join(words[j].get("word", "") for j in range(lo, hi))
    return re.sub(r"\s+", " ", snippet).strip()


def nearest_visual_moment(script: dict | None, phrase: str, start_frame: int) -> dict | None:
    if not script:
        return None
    norm_phrase = normalize(phrase)
    best: dict | None = None
    best_dist = 999999
    for vm in script.get("visual_moments") or []:
        if not isinstance(vm, dict):
            continue
        at = vm.get("at_phrase") or ""
        norm_at = normalize(at)
        if norm_at and (norm_at in norm_phrase or norm_phrase in norm_at):
            return vm
    for vm in script.get("visual_moments") or []:
        if vm.get("type") != "step":
            continue
        at = normalize(vm.get("at_phrase") or "")
        if not at:
            continue
        dist = abs(start_frame - 0)
        if norm_phrase and at in norm_phrase:
            return vm
        if best is None:
            best = vm
    return best


def resolve_visual_brief(
    moment: dict,
    script: dict | None,
) -> str:
    if moment.get("visual_brief"):
        return str(moment["visual_brief"])

    keyword = moment.get("keyword") or moment.get("word") or ""
    triggers = (script or {}).get("video_triggers") or {}
    descriptions = triggers.get("broll_image_descriptions") or []
    broll_phrases = triggers.get("broll_phrases") or []
    norm_kw = normalize(keyword)

    for i, phrase in enumerate(broll_phrases):
        if phrase and (normalize(phrase) in norm_kw or norm_kw in normalize(phrase)):
            if i < len(descriptions) and descriptions[i]:
                return str(descriptions[i])

    vm = moment.get("visual_moment_ref")
    if isinstance(vm, dict) and vm.get("label"):
        label = vm.get("label", "")
        graphic = vm.get("graphic", "")
        return f"On-screen concept: {label}" + (f" ({graphic})" if graphic else "")

    templ = template_for_phrase(keyword)
    if templ:
        return templ

    return f"Abstract cinematic metaphor for: {keyword}"


def style_anchor(script: dict | None) -> str:
    brand = _load_brand()
    handle = brand.get("handle", "")
    title = (script or {}).get("title_overlay") or (script or {}).get("caption_hook") or ""
    territory = (script or {}).get("territory") or ""
    bits = [_STYLE_ANCHOR]
    if title:
        bits.append(f"Video topic: {title}.")
    if territory:
        bits.append(f"Territory: {territory}.")
    if handle:
        bits.append(f"Creator: {handle}.")
    return " ".join(bits)


def enrich_moment_context(moment: dict, transcript: dict, script: dict | None) -> dict:
    """Attach transcript_context and visual_moment_ref on the moment dict."""
    start = moment.get("start_frame", 0)
    words = transcript.get("words", [])
    moment["transcript_context"] = transcript_window(words, start)
    vm = nearest_visual_moment(script, moment.get("keyword", ""), start)
    if vm:
        moment["visual_moment_ref"] = {
            "at_phrase": vm.get("at_phrase"),
            "label": vm.get("label"),
            "graphic": vm.get("graphic"),
            "type": vm.get("type"),
        }
    return moment
