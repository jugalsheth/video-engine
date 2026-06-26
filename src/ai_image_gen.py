from __future__ import annotations

from pathlib import Path

from src import fal_client
from src.ai_cost_budget import AICostBudget
from src.broll_visual_context import (
    HARD_NEGATIVES,
    resolve_visual_brief,
    style_anchor,
)
from src.broll_vision_qa import check_broll_image, vision_qa_enabled
from src.pipeline_config import ai_image_max_per_video, ai_image_model, ai_images_enabled

ENGINE_ROOT = Path(__file__).resolve().parent.parent
PUBLIC_DIR = ENGINE_ROOT / "remotion" / "public"
AI_IMAGES_DIR = PUBLIC_DIR / "ai_images"

BG_STRIP_PREAMBLE = (
    "Full-screen vertical cinematic background. Dark unobtrusive lower 35% for speaker. "
    "Dramatic lighting. "
)
HOOK_IMMERSE_PREAMBLE = (
    "Bold cinematic scene, high contrast, scroll-stopping vertical frame. "
)
STYLE_PREAMBLE = (
    "Cinematic vertical 9:16 b-roll still for a tech creator short-form video. "
    "High contrast, modern. "
)


def _preamble_for_layout(layout: str | None) -> str:
    if layout == "immersive_flash":
        return HOOK_IMMERSE_PREAMBLE
    if layout in {"presenter_on_bg", "presenter_cutout", "greenscreen"}:
        return BG_STRIP_PREAMBLE
    return STYLE_PREAMBLE


def build_broll_prompt(moment: dict, script: dict | None = None) -> str:
    keyword = moment.get("keyword") or moment.get("word") or moment.get("type", "")
    layout = moment.get("layout")
    preamble = _preamble_for_layout(layout)

    visual_brief = resolve_visual_brief(moment, script)
    spoken = moment.get("transcript_context") or ""
    if spoken:
        spoken = f"Spoken context: {spoken}. "
    anchor = style_anchor(script)
    phrase_line = f"Illustrate the spoken phrase: {keyword}. " if keyword else ""

    body = (
        f"{phrase_line}"
        f"Visual: {visual_brief}. "
        f"{spoken}"
        f"{anchor} "
        f"{HARD_NEGATIVES}"
    )
    return f"{preamble}{body}"


def build_custom_prompt(description: str, script: dict | None = None) -> str:
    anchor = style_anchor(script)
    return (
        "Clean infographic or diagram for a vertical tech education video. "
        f"{description}. {anchor} "
        "Dark background, amber and cyan accents, readable layout, no watermark."
    )


def _needs_ai_fill(moment: dict) -> bool:
    if moment.get("clip_file"):
        return False
    if moment.get("image_file") and not moment.get("force_regenerate"):
        return False
    source = (moment.get("source") or "").lower()
    return source in {"", "svg", "failed", "script_broll_phrases", "ai_image"}


def clear_ai_images(output_dir: Path | None = None) -> int:
    base = output_dir or PUBLIC_DIR
    images_dir = base / "ai_images"
    if not images_dir.exists():
        return 0
    removed = 0
    for f in images_dir.glob("moment_*.png"):
        f.unlink(missing_ok=True)
        removed += 1
    return removed


def fill_broll_moments(
    broll_result: dict,
    script: dict | None = None,
    *,
    output_dir: Path | None = None,
    budget: AICostBudget | None = None,
    project_id: str = "",
    regenerate: bool = False,
) -> dict:
    """
    Generate AI stills for B-roll moments without stock clips.
    Sets moment['image_file'] and moment['source']='ai_image' on success.
    """
    summary = {
        "generated": 0,
        "cached": 0,
        "failed": 0,
        "skipped": 0,
        "cost_usd": 0.0,
        "model": ai_image_model(),
    }

    if not ai_images_enabled():
        summary["skipped"] = len(broll_result.get("moments", []))
        return summary

    base_dir = output_dir or PUBLIC_DIR
    images_dir = base_dir / "ai_images"
    images_dir.mkdir(parents=True, exist_ok=True)

    if regenerate:
        cleared = clear_ai_images(base_dir)
        if cleared:
            print(f"   Cleared {cleared} cached AI b-roll image(s) for regeneration")

    cost_budget = budget or AICostBudget()
    budget_count = ai_image_max_per_video()
    used = 0

    for moment in broll_result.get("moments", []):
        if regenerate:
            moment.pop("image_file", None)
            moment["force_regenerate"] = True

        if not _needs_ai_fill(moment):
            summary["skipped"] += 1
            continue
        if used >= budget_count or not cost_budget.can_spend():
            summary["skipped"] += 1
            continue

        moment_id = f"moment_{moment['start_frame']}"
        rel_path = f"ai_images/{moment_id}.png"
        dest = base_dir / rel_path
        prompt = build_broll_prompt(moment, script)
        moment["visual_brief"] = resolve_visual_brief(moment, script)

        cache_ns = f"{project_id}:{moment['start_frame']}" if project_id else str(moment["start_frame"])

        path, meta = fal_client.generate_image(
            prompt,
            dest=dest,
            model=ai_image_model(),
            cache_namespace=cache_ns,
        )
        used += 1
        if path:
            moment["image_file"] = rel_path
            moment["source"] = "ai_image"
            moment["ai_prompt"] = prompt
            moment.pop("force_regenerate", None)
            if meta.get("cached"):
                summary["cached"] += 1
            else:
                summary["generated"] += 1
            cost = float(meta.get("cost_usd", 0))
            if not cost_budget.charge(cost):
                summary["failed"] += 1
                continue
            summary["cost_usd"] = round(summary["cost_usd"] + cost, 4)

            if vision_qa_enabled():
                phrase = moment.get("keyword") or moment.get("word") or ""
                brief = moment.get("visual_brief") or resolve_visual_brief(moment, script)
                passed, reason = check_broll_image(dest, phrase, brief)
                if not passed:
                    print(f"   Vision QA fail ({phrase}): {reason}")
                    retry_prompt = f"{prompt} Extra emphasis: {brief}. Strictly no people, faces, or text."
                    retry_ns = f"{cache_ns}:qa-retry"
                    retry_path, retry_meta = fal_client.generate_image(
                        retry_prompt,
                        dest=dest,
                        model=ai_image_model(),
                        cache_namespace=retry_ns,
                        use_cache=False,
                    )
                    if retry_path:
                        moment["ai_prompt"] = retry_prompt
                        moment["vision_qa_retried"] = True
                        if not retry_meta.get("cached"):
                            summary["generated"] += 1
                            retry_cost = float(retry_meta.get("cost_usd", 0))
                            cost_budget.charge(retry_cost)
                            summary["cost_usd"] = round(summary["cost_usd"] + retry_cost, 4)
                    else:
                        moment["vision_qa_failed"] = reason
        else:
            summary["failed"] += 1

    print(
        f"   AI B-roll: {summary['generated']} generated, {summary['cached']} cached, "
        f"{summary['failed']} failed, ${summary['cost_usd']:.3f} est."
    )
    return summary


def ensure_custom_visual_assets(
    script: dict | None,
    assets_dir: Path,
    dest_dir: Path,
) -> tuple[dict | None, dict]:
    """
    Generate PNGs for custom_visual_overrides with asset_status needs_creation.
    Manual assets in assets_dir always win.
    """
    summary = {
        "generated": 0,
        "cached": 0,
        "failed": 0,
        "cost_usd": 0.0,
    }
    if not script or not ai_images_enabled():
        return script, summary

    overrides = list(script.get("custom_visual_overrides") or [])
    if not overrides:
        return script, summary

    from src.asset_matcher import resolve_overrides

    script, matched = resolve_overrides(script, assets_dir)
    if matched:
        return script, summary

    assets_dir.mkdir(parents=True, exist_ok=True)
    dest_dir.mkdir(parents=True, exist_ok=True)
    updated_overrides: list[dict] = []
    budget = ai_image_max_per_video()

    for i, override in enumerate(overrides):
        entry = dict(override)
        if entry.get("asset_status") == "ready":
            updated_overrides.append(entry)
            continue
        if summary["generated"] + summary["cached"] >= budget:
            updated_overrides.append(entry)
            continue

        description = entry.get("description") or entry.get("trigger_phrase", "custom visual")
        trigger = entry.get("trigger_phrase", f"custom_{i}")
        from src.project_paths import slugify

        slug = slugify(trigger) or f"custom_{i}"
        filename = f"{slug}.png"
        asset_path = assets_dir / filename
        prompt = build_custom_prompt(description, script)

        path, meta = fal_client.generate_image(
            prompt,
            dest=asset_path,
            model="nano-banana",
            cache_namespace=f"custom:{slug}",
        )
        if path:
            import shutil
            shutil.copy2(asset_path, dest_dir / filename)
            shutil.copy2(asset_path, dest_dir / "asset.png")
            entry["asset_status"] = "ready"
            entry["asset_filename"] = filename
            entry["ai_generated"] = True
            if meta.get("cached"):
                summary["cached"] += 1
            else:
                summary["generated"] += 1
            summary["cost_usd"] = round(summary["cost_usd"] + float(meta.get("cost_usd", 0)), 4)
            print(f"   AI custom visual: {filename}")
        else:
            summary["failed"] += 1
        updated_overrides.append(entry)

    if summary["generated"] or summary["cached"]:
        script = dict(script)
        script["custom_visual_overrides"] = updated_overrides

    return script, summary
