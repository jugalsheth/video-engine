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


def _cache_key(query: str, source: str, seed: str = "") -> str:
    raw = f"{source}:{query}:{seed}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def _pick_index(seed: str, count: int) -> int:
    if count <= 0:
        return 0
    return int(hashlib.md5(seed.encode()).hexdigest(), 16) % count


def _collect_pexels_urls(videos: list[dict]) -> list[str]:
    urls: list[str] = []
    for video in videos:
        files = sorted(
            video.get("video_files", []),
            key=lambda f: f.get("width", 0),
            reverse=True,
        )
        picked = False
        for f in files:
            link = f.get("link")
            if link and f.get("width", 0) <= 1080:
                urls.append(link)
                picked = True
                break
        if not picked and files and files[0].get("link"):
            urls.append(files[0]["link"])
    return urls


def _fetch_pexels(query: str, api_key: str, seed: str) -> str | None:
    url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": api_key}
    params = {"query": query, "orientation": "portrait", "per_page": 15, "size": "medium"}
    try:
        r = httpx.get(url, headers=headers, params=params, timeout=15)
        r.raise_for_status()
        urls = _collect_pexels_urls(r.json().get("videos", []))
        if not urls:
            return None
        return urls[_pick_index(seed, len(urls))]
    except Exception as e:
        print(f"   Pexels search failed for '{query}': {e}")
    return None


def _collect_pixabay_urls(hits: list[dict]) -> list[str]:
    urls: list[str] = []
    for hit in hits:
        videos = hit.get("videos", {})
        for quality in ("medium", "small", "tiny"):
            v = videos.get(quality, {})
            if v.get("url"):
                urls.append(v["url"])
                break
    return urls


def _fetch_pixabay(query: str, api_key: str, seed: str) -> str | None:
    url = "https://pixabay.com/api/videos/"
    params = {"key": api_key, "q": query, "per_page": 15}
    try:
        r = httpx.get(url, params=params, timeout=15)
        r.raise_for_status()
        urls = _collect_pixabay_urls(r.json().get("hits", []))
        if not urls:
            return None
        return urls[_pick_index(seed, len(urls))]
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
    if skip_stock_fetch() or mode in ("svg", "ai"):
        for moment in broll_result.get("moments", []):
            moment["search_query"] = _search_query(moment, search_map)
            moment["source"] = "svg" if mode == "svg" else moment.get("source", "pending_ai")
        reason = "zero-cost mode" if skip_stock_fetch() else f"{mode} mode"
        print(f"   Stock B-roll: skipped ({reason}, SVG/AI fallback)")
        return {"fetched": 0, "cached": 0, "failed": 0, "sources": [], "svg_only": mode == "svg", "ai_pending": mode == "ai"}

    if not pexels_key and not pixabay_key:
        print("   Stock B-roll: no PEXELS_API_KEY or PIXABAY_API_KEY — using SVG fallback")
        print("   Add keys to CretorAuto/.env (see video-engine/.env.example)")

    for moment in broll_result.get("moments", []):
        query = _search_query(moment, search_map)
        moment["search_query"] = query
        moment_id = f"moment_{moment['start_frame']}"
        clip_rel = f"broll_clips/{moment_id}.mp4"
        clip_path = PUBLIC_DIR / clip_rel
        cache_seed = f"{query}:{moment_id}"

        cache_file = CACHE_DIR / f"{_cache_key(query, 'stock', cache_seed)}.mp4"
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
            video_url = _fetch_pexels(query, pexels_key, cache_seed)
            source = "pexels"
        if not video_url and pixabay_key:
            video_url = _fetch_pixabay(query, pixabay_key, cache_seed)
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
