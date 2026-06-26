from __future__ import annotations

import re
from pathlib import Path

ENGINE_ROOT = Path(__file__).resolve().parent.parent

INBOX_DIR = ENGINE_ROOT / "inbox"
PROJECTS_DIR = ENGINE_ROOT / "projects"
LEGACY_RAW_DIR = ENGINE_ROOT / "raw_videos"
LEGACY_OUTPUT_DIR = ENGINE_ROOT / "ready_to_post"

ASSET_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".mp4"}


def slugify(name: str) -> str:
    """Canonical project folder name from filename_hint or video stem."""
    stem = Path(name).stem.lower()
    stem = re.sub(r"[^a-z0-9]+", "_", stem)
    stem = re.sub(r"_+", "_", stem).strip("_")
    return stem or "untitled"


def project_id_from_script(script: dict) -> str:
    hint = script.get("filename_hint") or f"script_{script.get('script_number', 'unknown')}"
    return slugify(hint)


def project_dir(project_id: str) -> Path:
    return PROJECTS_DIR / project_id


def raw_path(project_id: str) -> Path:
    return project_dir(project_id) / "raw.mp4"


def transcript_path(project_id: str) -> Path:
    return project_dir(project_id) / "transcript.json"


def final_path(project_id: str) -> Path:
    return project_dir(project_id) / "final.mp4"


def assets_dir(project_id: str) -> Path:
    return project_dir(project_id) / "assets"


def meta_path(project_id: str) -> Path:
    return project_dir(project_id) / "meta.json"


def staging_dir(project_id: str) -> Path:
    return project_dir(project_id) / "staging"


def shot_list_checkpoint(project_id: str) -> Path:
    return project_dir(project_id) / "shot_list.json"


def source_cut_path(project_id: str) -> Path:
    return project_dir(project_id) / "source_cut.mp4"
