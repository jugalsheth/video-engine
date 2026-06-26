from __future__ import annotations

import json
import shutil
from pathlib import Path

from src.project_paths import ENGINE_ROOT, project_dir

PUBLIC_DIR = ENGINE_ROOT / "remotion" / "public"


def project_staging_dir(project_id: str) -> Path:
    return project_dir(project_id) / "staging"


def resolve_output_dir(project_assets_dir: Path | None) -> tuple[Path, str]:
    """Return (write_dir, project_id). Uses project staging when assets dir is set."""
    if project_assets_dir and project_assets_dir.parent.name:
        project_id = project_assets_dir.parent.name
        out = project_staging_dir(project_id)
        out.mkdir(parents=True, exist_ok=True)
        return out, project_id
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    return PUBLIC_DIR, ""


def sync_staging_to_public(staging: Path) -> None:
    if staging.resolve() == PUBLIC_DIR.resolve():
        return
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    for item in staging.iterdir():
        dest = PUBLIC_DIR / item.name
        if item.is_dir():
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)


def checkpoint_shot_list(project_id: str, shot_list: dict) -> Path:
    path = project_dir(project_id) / "shot_list.json"
    path.write_text(json.dumps(shot_list, indent=2), encoding="utf-8")
    return path


def write_input_props(project_id: str, render_props: dict, transcript: dict) -> Path:
    props = {
        **render_props,
        "total_frames": transcript.get("total_frames"),
        "fps": transcript.get("fps", 30),
    }
    path = project_dir(project_id) / "input-props.json"
    path.write_text(json.dumps(props, indent=2), encoding="utf-8")
    staging = project_staging_dir(project_id)
    staging.mkdir(parents=True, exist_ok=True)
    (staging / "input-props.json").write_text(json.dumps(props, indent=2), encoding="utf-8")
    return path
