from __future__ import annotations

import json
import os
from pathlib import Path

import httpx

from src.pipeline_config import zero_cost_mode

ENGINE_ROOT = Path(__file__).resolve().parent.parent
MUSIC_DIR = ENGINE_ROOT / "remotion" / "public" / "music"
LIBRARY_PATH = ENGINE_ROOT / "rules" / "music_library.json"
DEFAULT_TRACK = MUSIC_DIR / "background.mp3"


def _load_library() -> dict:
    if not LIBRARY_PATH.exists():
        return {"tracks": {}, "default": "calm", "legacy_file": "background.mp3"}
    return json.loads(LIBRARY_PATH.read_text(encoding="utf-8"))


def pick_track(script: dict | None, template: dict | None) -> dict:
    """Return music config for Remotion AudioLayer."""
    lib = _load_library()
    tracks = lib.get("tracks", {})
    key = lib.get("default", "calm")

    if script:
        hook = (script.get("hook_type") or "").strip().upper()
        hook_map = lib.get("hook_type_map", {})
        if hook in hook_map:
            key = hook_map[hook]

    if template:
        tpl_id = (template.get("id") or "").strip().upper()
        tpl_map = lib.get("template_map", {})
        if tpl_id in tpl_map:
            key = tpl_map[tpl_id]

    track = tracks.get(key) or tracks.get(lib.get("default", "calm")) or {}
    filename = track.get("file") or lib.get("legacy_file", "background.mp3")
    return {
        "key": key,
        "file": filename,
        "volume_speaking": track.get("volume_speaking", 0.03),
        "volume_idle": track.get("volume_idle", 0.07),
    }


def _download_pixabay_track(dest: Path, queries: list[str]) -> bool:
    api_key = os.getenv("PIXABAY_API_KEY", "")
    if not api_key or zero_cost_mode():
        return False

    MUSIC_DIR.mkdir(parents=True, exist_ok=True)
    url = "https://pixabay.com/api/"
    for query in queries:
        try:
            r = httpx.get(
                url,
                params={"key": api_key, "q": query, "audio_type": "music", "per_page": 5},
                timeout=15,
            )
            r.raise_for_status()
            for hit in r.json().get("hits", []):
                audio_url = hit.get("previewURL") or hit.get("audio")
                if not audio_url:
                    continue
                with httpx.stream("GET", audio_url, timeout=60, follow_redirects=True) as resp:
                    resp.raise_for_status()
                    with dest.open("wb") as f:
                        for chunk in resp.iter_bytes():
                            f.write(chunk)
                if dest.exists() and dest.stat().st_size > 5000:
                    return True
        except Exception:
            continue
    return False


def _ensure_track_file(key: str, spec: dict) -> Path | None:
    dest = MUSIC_DIR / spec.get("file", f"{key}.mp3")
    if dest.exists() and dest.stat().st_size > 5000:
        return dest

    if _download_pixabay_track(dest, spec.get("pixabay_queries", [])):
        print(f"   Music: {spec.get('file')} ({spec.get('label', key)}) from Pixabay")
        return dest

    legacy = MUSIC_DIR / _load_library().get("legacy_file", "background.mp3")
    if legacy.exists() and legacy.stat().st_size > 5000:
        dest.write_bytes(legacy.read_bytes())
        print(f"   Music: {spec.get('file')} (copied from legacy bed)")
        return dest

    return None


def ensure_background_music(script: dict | None = None, template: dict | None = None) -> dict:
    """Ensure library tracks exist; return picked track config for this video."""
    lib = _load_library()
    MUSIC_DIR.mkdir(parents=True, exist_ok=True)

    for key, spec in lib.get("tracks", {}).items():
        _ensure_track_file(key, spec)

    picked = pick_track(script, template)
    track_path = MUSIC_DIR / picked["file"]
    if not track_path.exists() or track_path.stat().st_size <= 5000:
        legacy = DEFAULT_TRACK
        if legacy.exists() and legacy.stat().st_size > 5000:
            track_path.write_bytes(legacy.read_bytes())
            picked["file"] = legacy.name
        else:
            print("   Music: no bed found — run scripts/download_assets.py")

    return picked


def ensure_background_music_legacy() -> Path | None:
    """Backward-compatible single-track fetch."""
    result = ensure_background_music()
    path = MUSIC_DIR / result["file"]
    return path if path.exists() else None
