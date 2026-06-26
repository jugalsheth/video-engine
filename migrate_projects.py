#!/usr/bin/env python3
"""
One-time migration: flat raw_videos/ + ready_to_post/ → projects/{id}/.

Usage:
  python migrate_projects.py          # dry run
  python migrate_projects.py --apply  # move files
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from src.project_manager import ensure_dirs, write_meta
from src.project_paths import (
    LEGACY_OUTPUT_DIR,
    LEGACY_RAW_DIR,
    PROJECTS_DIR,
    assets_dir,
    final_path,
    raw_path,
    slugify,
    transcript_path,
)

ENGINE_ROOT = Path(__file__).resolve().parent


def _find_final_for_raw(stem: str, finals: list[Path]) -> Path | None:
    stem_lower = stem.lower()
    stem_slug = slugify(stem)

    best: Path | None = None
    best_score = 0
    for final in finals:
        name = final.stem.lower()
        if stem_lower in name or stem_slug in slugify(name):
            score = len(stem_lower)
            if score > best_score:
                best = final
                best_score = score
    return best


def _migrate_custom_assets(raw_dir: Path, project_id: str, apply: bool) -> list[str]:
    legacy_assets = raw_dir / "custom_assets"
    if not legacy_assets.exists():
        return []

    moved: list[str] = []
    dest = assets_dir(project_id)
    for sub in legacy_assets.iterdir():
        if not sub.is_dir():
            continue
        if slugify(sub.name) != project_id and sub.name != project_id:
            continue
        for f in sub.iterdir():
            if f.is_file():
                moved.append(f.name)
                if apply:
                    dest.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(f), str(dest / f.name))
    return moved


def migrate(apply: bool = False) -> list[dict]:
    ensure_dirs()
    raw_files = sorted(LEGACY_RAW_DIR.glob("*.mp4")) if LEGACY_RAW_DIR.exists() else []
    final_files = sorted(LEGACY_OUTPUT_DIR.glob("*.mp4")) if LEGACY_OUTPUT_DIR.exists() else []
    remaining_finals = list(final_files)
    report: list[dict] = []

    for raw in raw_files:
        project_id = slugify(raw.stem)
        final = _find_final_for_raw(raw.stem, remaining_finals)
        if final and final in remaining_finals:
            remaining_finals.remove(final)

        sidecar = LEGACY_RAW_DIR / f"{raw.stem}_transcript.json"
        entry = {
            "project_id": project_id,
            "raw": raw.name,
            "final": final.name if final else None,
            "transcript": sidecar.name if sidecar.exists() else None,
        }
        report.append(entry)

        if not apply:
            continue

        dest = PROJECTS_DIR / project_id
        dest.mkdir(parents=True, exist_ok=True)
        assets_dir(project_id).mkdir(exist_ok=True)

        if not raw_path(project_id).exists():
            shutil.move(str(raw), str(raw_path(project_id)))
        if sidecar.exists() and not transcript_path(project_id).exists():
            shutil.move(str(sidecar), str(transcript_path(project_id)))
        if final and not final_path(project_id).exists():
            shutil.move(str(final), str(final_path(project_id)))

        assets = _migrate_custom_assets(LEGACY_RAW_DIR, project_id, apply=True)
        write_meta(
            project_id,
            status="rendered" if final else "migrated",
            raw_filename_original=entry["raw"],
            title=project_id.replace("_", " ").title(),
            paths={
                "raw": str(raw_path(project_id)),
                "final": str(final_path(project_id)) if final else None,
                "assets": str(assets_dir(project_id)),
            },
            custom_assets_found=assets,
        )

    unmatched_dir = PROJECTS_DIR / "_unmatched"
    if apply and remaining_finals:
        unmatched_dir.mkdir(parents=True, exist_ok=True)
        for final in remaining_finals:
            shutil.move(str(final), str(unmatched_dir / final.name))
            report.append({"project_id": "_unmatched", "final": final.name})

    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Move files (default is dry run)")
    args = parser.parse_args()

    report = migrate(apply=args.apply)
    print(json.dumps(report, indent=2))
    print()
    if args.apply:
        print(f"Migrated {len(report)} project(s) into projects/")
    else:
        print("Dry run — re-run with --apply to move files")


if __name__ == "__main__":
    main()
