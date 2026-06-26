from __future__ import annotations

"""
Auto-match PNG/JPG assets in a project assets/ folder to custom_visual_overrides.
No manual asset_status edits in scripts_archive.json required.
"""

import re
import shutil
from pathlib import Path

from src.project_paths import ASSET_EXTENSIONS, slugify


def _trigger_slug(trigger_phrase: str) -> str:
    return slugify(trigger_phrase)


def _list_assets(assets_dir: Path) -> list[Path]:
    if not assets_dir.exists():
        return []
    return sorted(
        f for f in assets_dir.iterdir()
        if f.is_file() and f.suffix.lower() in ASSET_EXTENSIONS
    )


def _match_file_to_override(files: list[Path], trigger_phrase: str) -> Path | None:
    slug = _trigger_slug(trigger_phrase)
    if not slug:
        return None

    for f in files:
        name = f.stem.lower()
        if slug in name or name in slug:
            return f

    for f in files:
        name = slugify(f.stem)
        if name and (name in slug or slug in name):
            return f

    return None


def resolve_overrides(script: dict | None, assets_dir: Path) -> tuple[dict | None, list[str]]:
    """
    Return a script copy with asset_status set to ready when matching files exist.
    Also returns list of asset filenames that were matched.
    """
    if not script:
        return script, []

    overrides = script.get("custom_visual_overrides") or []
    if not overrides:
        return script, []

    files = _list_assets(assets_dir)
    if not files:
        return script, []

    updated = dict(script)
    updated_overrides: list[dict] = []
    matched_names: list[str] = []

    unmatched_files = list(files)
    for override in overrides:
        entry = dict(override)
        trigger = entry.get("trigger_phrase", "")
        matched = _match_file_to_override(unmatched_files, trigger) if trigger else None

        if matched is None and len(unmatched_files) == 1 and len(overrides) == 1:
            matched = unmatched_files[0]

        if matched is not None:
            entry["asset_status"] = "ready"
            entry["asset_filename"] = matched.name
            matched_names.append(matched.name)
            if matched in unmatched_files:
                unmatched_files.remove(matched)
        updated_overrides.append(entry)

    updated["custom_visual_overrides"] = updated_overrides
    return updated, matched_names


def stage_assets_for_remotion(
    script: dict | None,
    assets_dir: Path,
    dest_dir: Path,
) -> int:
    """
    Copy matched project assets into remotion/public/custom_assets/{script_id}/.
    Primary matched file is also copied as asset.png for CustomVisual.
    """
    if not script:
        return 0

    script, _ = resolve_overrides(script, assets_dir)
    overrides = script.get("custom_visual_overrides") or []
    ready = [o for o in overrides if o.get("asset_status") == "ready"]
    if not ready:
        return 0

    dest_dir.mkdir(parents=True, exist_ok=True)
    copied = 0

    for i, override in enumerate(ready):
        filename = override.get("asset_filename")
        if not filename:
            continue
        src = assets_dir / filename
        if not src.exists():
            continue
        shutil.copy2(src, dest_dir / filename)
        copied += 1
        ext = src.suffix.lower()
        if i == 0 or len(ready) == 1:
            shutil.copy2(src, dest_dir / f"asset{ext}")
            if ext != ".png":
                shutil.copy2(src, dest_dir / "asset.png")

    return copied
