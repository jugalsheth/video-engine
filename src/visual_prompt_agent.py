from __future__ import annotations

import json
import os
import re
from pathlib import Path

from src.ai_cost_budget import AICostBudget
from src.broll_visual_context import template_for_phrase, transcript_window
from src.trigger_utils import resolve_phrase_frame

ENGINE_ROOT = Path(__file__).resolve().parent.parent
HAIKU_MODEL = "claude-haiku-4-5-20251001"
AGENT_COST_USD = 0.002


def ai_prompt_agent_enabled() -> bool:
    return os.getenv("AI_PROMPT_AGENT", "true").lower() in ("1", "true", "yes")


def _missing_description_indices(script: dict | None) -> list[int]:
    if not script:
        return []
    triggers = script.get("video_triggers") or {}
    phrases = triggers.get("broll_phrases") or []
    descriptions = triggers.get("broll_image_descriptions") or []
    missing: list[int] = []
    for i, phrase in enumerate(phrases):
        if not phrase:
            continue
        if i >= len(descriptions) or not descriptions[i]:
            missing.append(i)
    return missing


def _parse_json_object(text: str) -> dict | None:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                return None
    return None


def _call_haiku(prompt: str) -> str | None:
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}],
        )
        parts = []
        for block in message.content:
            if hasattr(block, "text"):
                parts.append(block.text)
        return "\n".join(parts) if parts else None
    except Exception as exc:
        print(f"   Visual prompt agent failed: {exc}")
        return None


def fill_missing_descriptions(
    script: dict | None,
    transcript: dict,
    *,
    budget: AICostBudget | None = None,
) -> tuple[dict | None, dict]:
    """
    Fill missing broll_image_descriptions via Haiku (batched).
    Returns updated script copy and summary.
    """
    summary = {"filled": 0, "skipped": 0, "cost_usd": 0.0, "used_agent": False}
    if not script or not ai_prompt_agent_enabled():
        return script, summary

    triggers = dict(script.get("video_triggers") or {})
    phrases = list(triggers.get("broll_phrases") or [])
    descriptions = list(triggers.get("broll_image_descriptions") or [])
    layouts = list(triggers.get("broll_layouts") or [])

    if not phrases:
        return script, summary

    while len(descriptions) < len(phrases):
        descriptions.append("")
    while len(layouts) < len(phrases):
        layouts.append("presenter_on_bg")

    missing = _missing_description_indices(script)
    if not missing:
        return script, summary

    cost_budget = budget or AICostBudget()
    if not cost_budget.can_spend(AGENT_COST_USD):
        summary["skipped"] = len(missing)
        return script, summary

    words = transcript.get("words", [])
    full_text = transcript.get("full_text", "")
    title = script.get("title_overlay", "")
    items = []
    for i in missing:
        phrase = phrases[i]
        frame, _ = resolve_phrase_frame(words, full_text, phrase)
        ctx = transcript_window(words, frame or 0)
        templ = template_for_phrase(phrase) or ""
        items.append({"index": i, "phrase": phrase, "context": ctx, "template_hint": templ})

    prompt = (
        "You write AI image prompts for vertical tech education b-roll backgrounds.\n"
        "Rules: no people, no faces, no suits, no server room stock photos, no legible text.\n"
        "Compositor needs dark lower 35% empty for speaker strip.\n"
        "Palette: dark bg, teal and amber accents.\n"
        f"Video title: {title}\n\n"
        "Return ONLY JSON: {\"descriptions\": {\"0\": \"...\", ...}} using the index keys provided.\n"
        f"Items:\n{json.dumps(items, indent=2)}"
    )

    raw = _call_haiku(prompt)
    if not raw:
        for item in items:
            i = item["index"]
            descriptions[i] = item["template_hint"] or f"Abstract cinematic metaphor for {phrases[i]}, no people"
            summary["filled"] += 1
    else:
        payload = _parse_json_object(raw) or {}
        desc_map = payload.get("descriptions") or {}
        for item in items:
            i = item["index"]
            val = desc_map.get(str(i)) or desc_map.get(i) or item["template_hint"]
            if not val:
                val = f"Abstract cinematic metaphor for {phrases[i]}, no people"
            descriptions[i] = str(val)
            summary["filled"] += 1
        summary["used_agent"] = True
        if cost_budget.charge(AGENT_COST_USD):
            summary["cost_usd"] = AGENT_COST_USD

    updated = dict(script)
    triggers["broll_image_descriptions"] = descriptions
    triggers["broll_layouts"] = layouts
    updated["video_triggers"] = triggers
    if summary["filled"]:
        print(f"   Visual prompt agent: filled {summary['filled']} description(s)")
    return updated, summary


def write_prompt_manifest(
    broll_result: dict,
    script: dict | None,
    dest: Path,
) -> Path:
    entries = []
    for m in broll_result.get("moments", []):
        entries.append({
            "start_frame": m.get("start_frame"),
            "keyword": m.get("keyword"),
            "layout": m.get("layout"),
            "visual_brief": m.get("visual_brief"),
            "transcript_context": m.get("transcript_context"),
            "visual_moment_ref": m.get("visual_moment_ref"),
            "ai_prompt": m.get("ai_prompt"),
            "image_file": m.get("image_file"),
        })
    manifest = {
        "title": (script or {}).get("title_overlay"),
        "moments": entries,
        "video_triggers": (script or {}).get("video_triggers"),
    }
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return dest
