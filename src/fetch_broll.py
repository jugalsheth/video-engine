from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

import httpx

from src.pipeline_config import broll_mode, skip_stock_fetch

ENGINE_ROOT = Path(__file__).resolve().parent.parent
PUBLIC_DIR = ENGINE_ROOT / "remotion" / "public"
CLIPS_DIR = PUBLIC_DIR / "broll_clips"
CACHE_DIR = PUBLIC_DIR / "broll_cache"
SEARCH_MAP_PATH = ENGINE_ROOT / "rules" / "broll_search_map.txt"


def _load_search_map() -> dict[str, str]:
    mapping: dict[str, str] = {}
    if not SEARCH_MAP_PATH.exists():
        return mapping
    for line in SEARCH_MAP_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "→" in line:
            key, query = line.split("→", 1)
            mapping[key.strip()] = query.strip()
    return mapping


def _search_query(moment: dict, search_map: dict[str, str]) -> str:
    broll_type = moment.get("type", "")
    if moment.get("search_query"):
        return moment["search_query"]
    return search_map.get(broll_type, broll_type.replace("_", " "))


def _cache_key(query: str, source: str) -> str:
    return hashlib.md5(f"{source}:{query}".encode()).hexdigest()[:16]


def _fetch_pexels(query: str, api_key: str) -> str | None:
    url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": api_key}
    params = {"query": query, "orientation": "portrait", "per_page": 5, "size": "medium"}
    try:
        r = httpx.get(url, headers=headers, params=params, timeout=15)
        r.raise_for_status()
        videos = r.json().get("videos", [])
        for video in videos:
            files = sorted(
                video.get("video_files", []),
                key=lambda f: f.get("width", 0),
                reverse=True,
            )
            for f in files:
                link = f.get("link")
                if link and f.get("width", 0) <= 1080:
                    return link
            if files:
                return files[0].get("link")
    except Exception as e:
        print(f"   Pexels search failed for '{query}': {e}")
    return None


def _fetch_pixabay(query: str, api_key: str) -> str | None:
    url = "https://pixabay.com/api/videos/"
    params = {"key": api_key, "q": query, "per_page": 5}
    try:
        r = httpx.get(url, params=params, timeout=15)
        r.raise_for_status()
        hits = r.json().get("hits", [])
        for hit in hits:
            videos = hit.get("videos", {})
            for quality in ("medium", "small", "tiny"):
                v = videos.get(quality, {})
                if v.get("url"):
                    return v["url"]
    except Exception as e:
        print(f"   Pixabay search failed for '{query}': {e}")
    return None


def _download_video(url: str, dest: Path) -> bool:
    try:
        with httpx.stream("GET", url, timeout=60, follow_redirects=True) as r:
            r.raise_for_status()
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open("wb") as f:
                for chunk in r.iter_bytes():
                    f.write(chunk)
        return dest.exists() and dest.stat().st_size > 1000
    except Exception as e:
        print(f"   Download failed: {e}")
        return False


def fetch_all(broll_result: dict) -> dict:
    """
    Downloads stock clips for each B-roll moment.
    Returns summary: {fetched, cached, failed, sources}
    """
    pexels_key = os.getenv("PEXELS_API_KEY", "")
    pixabay_key = os.getenv("PIXABAY_API_KEY", "")
    search_map = _load_search_map()

    CLIPS_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    fetched = 0
    cached = 0
    failed = 0
    sources: list[str] = []

    mode = broll_mode()
    if skip_stock_fetch() or mode == "svg":
        for moment in broll_result.get("moments", []):
            moment["search_query"] = _search_query(moment, search_map)
            moment["source"] = "svg"
        print(f"   Stock B-roll: skipped ({mode} mode, SVG/greenscreen fallback)")
        return {"fetched": 0, "cached": 0, "failed": 0, "sources": [], "svg_only": True}

    for moment in broll_result.get("moments", []):
        query = _search_query(moment, search_map)
        moment["search_query"] = query
        moment_id = f"moment_{moment['start_frame']}"
        clip_rel = f"broll_clips/{moment_id}.mp4"
        clip_path = PUBLIC_DIR / clip_rel

        cache_file = CACHE_DIR / f"{_cache_key(query, 'stock')}.mp4"
        if cache_file.exists():
            import shutil
            shutil.copy2(cache_file, clip_path)
            moment["clip_file"] = clip_rel
            moment["source"] = "cache"
            cached += 1
            continue

        video_url = None
        source = None
        if pexels_key:
            video_url = _fetch_pexels(query, pexels_key)
            source = "pexels"
        if not video_url and pixabay_key:
            video_url = _fetch_pixabay(query, pixabay_key)
            source = "pixabay"

        if not video_url:
            moment["source"] = "svg"
            failed += 1
            continue

        if _download_video(video_url, clip_path):
            import shutil
            shutil.copy2(clip_path, cache_file)
            moment["clip_file"] = clip_rel
            moment["source"] = source
            fetched += 1
            sources.append(source or "unknown")
        else:
            failed += 1

    summary = {
        "fetched": fetched,
        "cached": cached,
        "failed": failed,
        "sources": sources,
    }
    print(
        f"   Stock B-roll: {fetched} fetched, {cached} cached, {failed} failed (SVG fallback)"
    )
    return summary
