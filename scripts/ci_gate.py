#!/usr/bin/env python3
"""CI gate: fail on trigger audit misses or shot list validation errors."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ENGINE_ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ENGINE_ROOT / "remotion" / "public"


def main() -> int:
    transcript_path = PUBLIC / "transcript.json"
    shot_list_path = PUBLIC / "shot_list.json"
    audit_path = PUBLIC / "trigger_audit.json"

    if not transcript_path.exists() or not shot_list_path.exists():
        print("Missing staged transcript or shot_list in remotion/public/")
        return 1

    transcript = json.loads(transcript_path.read_text())
    shot_list = json.loads(shot_list_path.read_text())

    from src.shot_list_validate import validate
    from src import trigger_audit

    errors = validate(shot_list, transcript.get("total_frames", 0))
    if errors:
        print("Shot list validation failed:")
        for err in errors[:5]:
            print(f"  - {err}")
        return 1

    script_meta = shot_list.get("script_metadata") or {}
    script = {
        "video_triggers": script_meta.get("video_triggers", {}),
        "visual_moments": script_meta.get("visual_moments", []),
        "spoken_script": transcript.get("full_text", ""),
    }
    audit = trigger_audit.audit(transcript, script, strict=True)
    if audit_path.exists():
        audit = json.loads(audit_path.read_text())
    elif not audit.get("passed"):
        return 1

    if audit.get("validation_errors"):
        print("Trigger audit validation errors:")
        for err in audit["validation_errors"]:
            print(f"  - {err}")
        return 1

    if not audit.get("passed"):
        print(f"Trigger audit failed: {len(audit.get('misses', []))} misses")
        return 1

    print("CI gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
