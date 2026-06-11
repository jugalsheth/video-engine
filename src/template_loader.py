from __future__ import annotations

import json
from pathlib import Path

ENGINE_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = ENGINE_ROOT / "rules" / "templates"

HOOK_TO_TEMPLATE = {
    "OPEN LOOP": "THREE_STEP_HOT_TAKE",
    "IDENTITY CALL": "THREE_STEP_HOT_TAKE",
    "CONTRARIAN STRIKE": "THREE_STEP_HOT_TAKE",
    "CONFESSION": "CONFESSION_STAT",
    "HOT TAKE": "THREE_STEP_HOT_TAKE",
}


def load_template(template_id: str) -> dict | None:
    path = TEMPLATES_DIR / f"{template_id.lower()}.json"
    if not path.exists():
        path = TEMPLATES_DIR / f"{template_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def resolve_template(script: dict | None) -> dict:
    """Pick edit template from script metadata or hook_type."""
    default = load_template("three_step_hot_take") or {}
    if not script:
        return default

    explicit = script.get("edit_template")
    if explicit:
        loaded = load_template(str(explicit))
        if loaded:
            return loaded

    hook = script.get("hook_type", "OPEN LOOP")
    template_id = HOOK_TO_TEMPLATE.get(hook, "THREE_STEP_HOT_TAKE")
    return load_template(template_id) or default
