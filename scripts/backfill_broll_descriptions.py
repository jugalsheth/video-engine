#!/usr/bin/env python3
"""Backfill broll_image_descriptions + broll_layouts in scripts_archive.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ENGINE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ENGINE_ROOT))

from src.broll_visual_context import template_for_phrase
from src.visual_prompt_agent import fill_missing_descriptions

ARCHIVE = ENGINE_ROOT / "data" / "scripts_archive.json"
SCRIPT_ENGINE_ARCHIVE = ENGINE_ROOT.parent / "script-engine" / "data" / "scripts_archive.json"


def _backfill_file(path: Path, *, dry_run: bool) -> int:
    if not path.exists():
        print(f"Skip missing: {path}")
        return 0
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        scripts = data
        wrapper = None
    else:
        scripts = data.get("scripts", [])
        wrapper = data
    updated = 0
    for script in scripts:
        triggers = script.get("video_triggers") or {}
        phrases = triggers.get("broll_phrases") or []
        if not phrases:
            continue
        descs = list(triggers.get("broll_image_descriptions") or [])
        layouts = list(triggers.get("broll_layouts") or [])
        while len(descs) < len(phrases):
            descs.append("")
        while len(layouts) < len(phrases):
            layouts.append("presenter_on_bg")
        missing = [i for i, p in enumerate(phrases) if not descs[i]]
        if not missing:
            continue
        transcript = {"words": [], "full_text": script.get("spoken_script", "")}
        filled_script, summary = fill_missing_descriptions(script, transcript)
        if filled_script:
            script["video_triggers"] = filled_script.get("video_triggers", triggers)
            for i in missing:
                phrase = phrases[i]
                if not script["video_triggers"]["broll_image_descriptions"][i]:
                    script["video_triggers"]["broll_image_descriptions"][i] = (
                        template_for_phrase(phrase)
                        or f"Abstract cinematic metaphor for {phrase}, no people"
                    )
            updated += 1
            print(f"  {script.get('filename_hint', script.get('title_overlay', '?'))}: filled {len(missing)}")
    if updated and not dry_run:
        if wrapper is not None:
            wrapper["scripts"] = scripts
            path.write_text(json.dumps(wrapper, indent=2), encoding="utf-8")
        else:
            path.write_text(json.dumps(scripts, indent=2), encoding="utf-8")
    return updated


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    total = 0
    for path in (ARCHIVE, SCRIPT_ENGINE_ARCHIVE):
        print(f"Backfilling {path}...")
        total += _backfill_file(path, dry_run=args.dry_run)
    print(f"Updated {total} script(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
