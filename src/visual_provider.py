"""Cost-tiered visual provider — Remotion/fal default, optional Higgsfield hero.

Automation: install CLI + `higgsfield auth login` once. Then build_composition
calls Higgsfield when hook_visual.tier=higgsfield (max 1/video). Failures fall
back to fal so renders never block.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from src import fal_client
from src import higgsfield_client
from src.ai_cost_budget import AICostBudget
from src.pipeline_config import ai_images_enabled, zero_cost_mode

ENGINE_ROOT = Path(__file__).resolve().parent.parent
PUBLIC_DIR = ENGINE_ROOT / "remotion" / "public"


def higgsfield_max_per_video() -> int:
    try:
        return max(0, int(os.getenv("HIGGSFIELD_MAX_PER_VIDEO", "1")))
    except ValueError:
        return 1


def _find_ready_hero(project_dir: Path | None, hook_visual: dict) -> Path | None:
    asset_file = hook_visual.get("asset_file")
    if project_dir and asset_file:
        candidate = project_dir / asset_file
        if candidate.exists():
            return candidate
    if project_dir:
        for base in (project_dir / "assets", project_dir):
            for name in ("hook_hero.png", "hook_hero.jpg", "hook_hero.webp", "hook_hero.mp4"):
                candidate = base / name
                if candidate.exists():
                    return candidate
    if hook_visual.get("asset_status") == "ready" and asset_file:
        p = Path(asset_file)
        if p.exists():
            return p
    return None


def _path_rel(dest: Path, out_base: Path) -> str:
    try:
        return str(dest.relative_to(out_base))
    except ValueError:
        return str(dest)


def _try_higgsfield(prompt: str, dest: Path, hook: dict, summary: dict) -> bool:
    if higgsfield_max_per_video() <= 0:
        summary["skipped_reason"] = "higgsfield_disabled"
        return False
    if not higgsfield_client.higgsfield_enabled():
        summary["skipped_reason"] = "higgsfield_cli_unavailable"
        return False

    print(f"   Higgsfield CLI → {higgsfield_client.model_name()} (hero still)")
    meta = higgsfield_client.generate_still(prompt, dest, aspect_ratio="9:16")
    if meta.get("ok") and dest.exists():
        summary["generated"] = 1
        summary["tier"] = "higgsfield"
        hook["asset_status"] = "ready"
        hook["higgsfield_url"] = meta.get("url")
        return True

    err = meta.get("error") or "unknown"
    print(f"   ⚠️ Higgsfield failed ({err}) — fal fallback")
    summary["skipped_reason"] = f"higgsfield_failed:{err[:80]}"
    return False


def resolve_hook_visual(
    script: dict | None,
    *,
    project_dir: Path | None = None,
    output_dir: Path | None = None,
    budget: AICostBudget | None = None,
    project_id: str = "",
) -> dict:
    summary: dict = {
        "tier": "none",
        "path": None,
        "generated": 0,
        "cached": 0,
        "failed": 0,
        "cost_usd": 0.0,
        "skipped_reason": None,
    }
    if not script:
        summary["skipped_reason"] = "no_script"
        return summary

    hook = script.get("hook_visual")
    if not isinstance(hook, dict):
        summary["skipped_reason"] = "no_hook_visual"
        return summary

    tier = (hook.get("tier") or "fal").lower()
    summary["tier"] = tier
    out_base = output_dir or PUBLIC_DIR
    heroes_dir = out_base / "ai_images" / "heroes"
    heroes_dir.mkdir(parents=True, exist_ok=True)
    dest = heroes_dir / "hook_hero.png"

    ready = _find_ready_hero(project_dir, hook)
    if ready:
        if ready.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
            shutil.copy2(ready, dest)
            summary["path"] = _path_rel(dest, out_base)
            summary["cached"] = 1
            summary["tier"] = tier if tier == "higgsfield" else "asset"
            hook["asset_status"] = "ready"
            hook["resolved_file"] = summary["path"]
            return summary
        summary["path"] = str(ready)
        summary["cached"] = 1
        hook["resolved_file"] = summary["path"]
        return summary

    prompt = (hook.get("prompt") or "").strip()

    if tier == "higgsfield" and prompt and not zero_cost_mode():
        if _try_higgsfield(prompt, dest, hook, summary):
            summary["path"] = _path_rel(dest, out_base)
            hook["resolved_file"] = summary["path"]
            if project_dir:
                assets = project_dir / "assets" if (project_dir / "assets").exists() or project_dir.name != "assets" else project_dir
                if project_dir.name == "assets":
                    assets = project_dir
                else:
                    assets = project_dir / "assets"
                assets.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dest, assets / "hook_hero.png")
            return summary
        tier = "fal"
        summary["tier"] = "fal_fallback"

    if tier == "remotion":
        summary["skipped_reason"] = "remotion_overlay_only"
        return summary

    if zero_cost_mode() or not ai_images_enabled():
        summary["skipped_reason"] = summary.get("skipped_reason") or "zero_cost_or_disabled"
        return summary

    if not prompt:
        summary["skipped_reason"] = "empty_prompt"
        return summary

    if budget is not None:
        est = fal_client.estimate_cost(count=1)
        if not budget.can_spend(est):
            summary["skipped_reason"] = "budget"
            return summary

    try:
        path, meta = fal_client.generate_image(
            prompt,
            dest=dest,
            size="portrait_16_9",
            cache_namespace=project_id or "hook",
        )
        if path and dest.exists():
            if meta.get("cached"):
                summary["cached"] = 1
            else:
                summary["generated"] = 1
            summary["path"] = _path_rel(dest, out_base)
            summary["cost_usd"] = float(meta.get("cost_usd") or 0)
            if budget is not None and summary["cost_usd"]:
                budget.charge(summary["cost_usd"])
            hook["resolved_file"] = summary["path"]
            hook["asset_status"] = "ready"
        else:
            summary["failed"] = 1
            summary["skipped_reason"] = meta.get("error") or "generate_failed"
    except Exception as exc:
        print(f"   ⚠️ Hook visual generation failed: {exc}")
        summary["failed"] = 1

    return summary
