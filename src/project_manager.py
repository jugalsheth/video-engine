from __future__ import annotations

"""
Project-folder lifecycle: inbox ingest, meta.json, raw/final paths.
"""

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from src.project_paths import (
    INBOX_DIR,
    LEGACY_RAW_DIR,
    PROJECTS_DIR,
    assets_dir,
    final_path,
    meta_path,
    project_dir,
    project_id_from_script,
    raw_path,
    slugify,
    transcript_path,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def match_by_filename(video_path: str | Path, scripts: list) -> dict | None:
    """Filename-only script match (before transcription)."""
    if not scripts:
        return None

    video_name = Path(video_path).stem.lower()
    for script in scripts:
        script_num = str(script.get("script_number", ""))
        if script_num and f"script_{script_num.zfill(2)}" in video_name:
            return script
        hint = Path(script.get("filename_hint", "")).stem.lower()
        if hint and hint in video_name:
            return script
    return None


def resolve_project_id(
    video_path: Path,
    script: dict | None = None,
    scripts: list | None = None,
) -> str:
    if script:
        return project_id_from_script(script)

    if scripts:
        matched = match_by_filename(video_path, scripts)
        if matched:
            return project_id_from_script(matched)

    return slugify(video_path.stem)


def ensure_dirs() -> None:
    INBOX_DIR.mkdir(exist_ok=True)
    PROJECTS_DIR.mkdir(exist_ok=True)


def ingest_video(
    video_path: str | Path,
    scripts: list | None = None,
    script: dict | None = None,
) -> tuple[str, Path, Path]:
    """
    Move an inbox/legacy raw MP4 into projects/{id}/raw.mp4.
    Returns (project_id, project_dir, raw_mp4_path).
    """
    ensure_dirs()
    source = Path(video_path).resolve()
    if not source.exists():
        raise FileNotFoundError(f"Video not found: {source}")

    # Already ingested: projects/{id}/raw.mp4
    if (
        source.parent.parent == PROJECTS_DIR
        and source.parent.name not in {"", ".", "_unmatched"}
        and source.name == "raw.mp4"
    ):
        pid = source.parent.name
        dest_dir = source.parent
        assets_dir(pid).mkdir(exist_ok=True)
        return pid, dest_dir, source

    pid = resolve_project_id(source, script=script, scripts=scripts)
    dest_dir = project_dir(pid)
    dest_dir.mkdir(parents=True, exist_ok=True)
    assets_dir(pid).mkdir(exist_ok=True)

    dest_raw = raw_path(pid)
    if source == dest_raw:
        return pid, dest_dir, dest_raw

    if source.parent.name in {"inbox", "raw_videos"} or source.parent == LEGACY_RAW_DIR:
        if dest_raw.exists():
            dest_raw.unlink()
        shutil.move(str(source), str(dest_raw))
        sidecar = source.parent / f"{source.stem}_transcript.json"
        if sidecar.exists():
            shutil.move(str(sidecar), str(transcript_path(pid)))
    elif not dest_raw.exists():
        shutil.copy2(str(source), str(dest_raw))

    return pid, dest_dir, dest_raw


def load_project_config(pid: str) -> dict:
    path = project_dir(pid) / "project_config.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def apply_project_config(
    pid: str,
    script: dict | None,
    transcript: dict | None = None,
) -> dict | None:
    """Merge project_config.json overrides; optionally skip archive script fields."""
    cfg = load_project_config(pid)
    if not cfg:
        return script

    if cfg.get("skip_archive_match"):
        script = {}

    if script is None:
        script = {}

    script = dict(script)
    for key in (
        "title_overlay",
        "subtitle_overlay",
        "hook_type",
        "caption_hook",
        "hashtags",
        "territory",
        "filename_hint",
        "visual_moments",
        "video_triggers",
        "social_moments",
        "edit_template",
    ):
        if key in cfg and cfg[key]:
            script[key] = cfg[key]

    overrides = list(cfg.get("custom_visual_overrides") or [])
    if overrides:
        script["custom_visual_overrides"] = overrides

    if not script.get("filename_hint"):
        script["filename_hint"] = f"{pid}.mp4"

    return script or None


def load_meta(pid: str) -> dict:
    path = meta_path(pid)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_meta(pid: str, **fields) -> dict:
    existing = load_meta(pid)
    existing.update(fields)
    existing.setdefault("project_id", pid)
    existing.setdefault("updated_at", _now_iso())
    meta_path(pid).write_text(json.dumps(existing, indent=2), encoding="utf-8")
    return existing


def init_meta(
    pid: str,
    *,
    raw_original: str,
    script: dict | None = None,
) -> dict:
    title = (script or {}).get("title_overlay", "")
    return write_meta(
        pid,
        project_id=pid,
        script_number=(script or {}).get("script_number"),
        title=title,
        status="processing",
        raw_filename_original=raw_original,
        matched_script_id=project_id_from_script(script) if script else None,
        created_at=_now_iso(),
        paths={
            "raw": str(raw_path(pid)),
            "final": str(final_path(pid)),
            "assets": str(assets_dir(pid)),
        },
    )


def mark_rendered(
    pid: str,
    *,
    output_path: str,
    script: dict | None,
    custom_assets_found: list[str],
    render_mins: float,
) -> dict:
    return write_meta(
        pid,
        status="rendered",
        rendered_at=_now_iso(),
        render_minutes=round(render_mins, 1),
        custom_assets_found=custom_assets_found,
        custom_assets_needed=len([
            o for o in (script or {}).get("custom_visual_overrides", [])
            if o.get("asset_status") != "ready"
        ]),
        paths={
            "raw": str(raw_path(pid)),
            "final": str(output_path),
            "assets": str(assets_dir(pid)),
        },
    )


def save_transcript(pid: str, transcript: dict) -> None:
    transcript_path(pid).write_text(json.dumps(transcript, indent=2), encoding="utf-8")


def list_projects() -> list[dict]:
    ensure_dirs()
    rows: list[dict] = []
    if not PROJECTS_DIR.exists():
        return rows

    for entry in sorted(PROJECTS_DIR.iterdir()):
        if not entry.is_dir() or entry.name.startswith("_"):
            continue
        pid = entry.name
        meta = load_meta(pid)
        has_raw = raw_path(pid).exists()
        has_final = final_path(pid).exists()
        asset_files = [
            f.name for f in assets_dir(pid).glob("*")
            if f.is_file() and f.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".mp4"}
        ] if assets_dir(pid).exists() else []

        overrides = meta.get("custom_visual_overrides") or []
        needed = len([o for o in overrides if o.get("asset_status") != "ready"])

        rows.append({
            "project_id": pid,
            "title": meta.get("title") or pid.replace("_", " ").title(),
            "status": meta.get("status") or ("rendered" if has_final else "raw_only"),
            "has_raw": has_raw,
            "has_final": has_final,
            "assets": asset_files,
            "custom_assets_needed": meta.get("custom_assets_needed", needed),
            "rendered_at": meta.get("rendered_at"),
            "paths": meta.get("paths", {
                "raw": str(raw_path(pid)),
                "final": str(final_path(pid)),
                "assets": str(assets_dir(pid)),
            }),
        })
    return rows
