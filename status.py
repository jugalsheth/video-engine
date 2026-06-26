#!/usr/bin/env python3
"""List all video projects and their status."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from dotenv import load_dotenv

ENGINE_ROOT = Path(__file__).resolve().parent
load_dotenv(ENGINE_ROOT.parent / ".env")
load_dotenv(ENGINE_ROOT / ".env")

from src.project_manager import list_projects  # noqa: E402


def _icon(row: dict) -> str:
    if row["has_final"]:
        return "✅"
    if row["has_raw"]:
        return "🎬"
    return "⬜"


def print_table(rows: list[dict]) -> None:
    if not rows:
        print("No projects yet. Drop a raw MP4 in inbox/ to start.")
        return

    print(f"{'':2} {'PROJECT':<42} {'STATUS':<12} {'FINAL':<6} {'ASSETS'}")
    print("-" * 80)
    for row in rows:
        assets = row.get("assets") or []
        needed = row.get("custom_assets_needed", 0)
        if assets:
            asset_str = f"{len(assets)} file(s)"
        elif needed:
            asset_str = f"needs {needed}"
        else:
            asset_str = "-"

        final = "yes" if row["has_final"] else "no"
        print(
            f"{_icon(row)} {row['project_id']:<42} "
            f"{row['status']:<12} {final:<6} {asset_str}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Show video project status")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    rows = list_projects()
    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        print_table(rows)
        print()
        print("Drop new recordings in inbox/")
        print("Optional PNGs: projects/{id}/assets/")
        print("Re-render: python watch.py --project {id}")


if __name__ == "__main__":
    main()
