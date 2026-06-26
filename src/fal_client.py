from __future__ import annotations

import base64
import hashlib
import os
import time
from pathlib import Path

import httpx

from src.pipeline_config import ai_image_model, fal_api_key

ENGINE_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ENGINE_ROOT / "remotion" / "public" / "ai_image_cache"

MODEL_ENDPOINTS: dict[str, str] = {
    "flux-schnell": "fal-ai/flux/schnell",
    "flux": "fal-ai/flux/schnell",
    "nano-banana": "fal-ai/nano-banana",
    "recraft": "fal-ai/recraft-v3/text-to-image",
}

# Rough USD per image for staging logs / meta.json (not billing-accurate).
MODEL_COST_USD: dict[str, float] = {
    "flux-schnell": 0.003,
    "flux": 0.003,
    "nano-banana": 0.04,
    "recraft": 0.04,
    "birefnet-light": 0.008,
}

PORTRAIT_SIZE = "portrait_16_9"
SQUARE_SIZE = "square_hd"
BIREFNET_ENDPOINT = "fal-ai/birefnet/v2"
CUTOUT_CACHE_DIR = ENGINE_ROOT / "remotion" / "public" / "ai_image_cache" / "cutouts"


def _resolve_endpoint(model: str | None = None) -> tuple[str, str]:
    key = (model or ai_image_model()).lower()
    endpoint = MODEL_ENDPOINTS.get(key, MODEL_ENDPOINTS["flux-schnell"])
    return key, endpoint


def _size_key(size: str | dict) -> str:
    if isinstance(size, str):
        return size
    return f"{size.get('width')}x{size.get('height')}"


def _cache_path(
    prompt: str,
    model: str,
    size: str | dict,
    cache_namespace: str = "",
) -> Path:
    ns = f"{cache_namespace}:" if cache_namespace else ""
    raw = f"{ns}{model}:{_size_key(size)}:{prompt}"
    digest = hashlib.sha256(raw.encode()).hexdigest()[:20]
    return CACHE_DIR / f"{digest}.png"


def _extract_image_url(payload: dict) -> str | None:
    images = payload.get("images") or []
    if images and isinstance(images[0], dict):
        url = images[0].get("url")
        if url:
            return url
    image = payload.get("image")
    if isinstance(image, dict) and image.get("url"):
        return image["url"]
    if isinstance(payload.get("url"), str):
        return payload["url"]
    return None


def estimate_cost(model: str | None = None, count: int = 1) -> float:
    key, _ = _resolve_endpoint(model)
    unit = MODEL_COST_USD.get(key, 0.01)
    return round(unit * count, 4)


def _download_image_bytes(image_url: str) -> bytes | None:
    if image_url.startswith("data:"):
        try:
            header, encoded = image_url.split(",", 1)
            return base64.b64decode(encoded)
        except Exception:
            return None
    try:
        with httpx.stream("GET", image_url, timeout=90, follow_redirects=True) as r:
            r.raise_for_status()
            return r.read()
    except Exception:
        return None


def generate_image(
    prompt: str,
    *,
    dest: Path,
    model: str | None = None,
    size: str | dict | None = None,
    use_cache: bool = True,
    max_retries: int = 2,
    cache_namespace: str = "",
) -> tuple[Path | None, dict]:
    """
    Generate a still image via fal.ai. Returns (path, meta).
    meta keys: source (cache|api|failed), model, cost_usd, cached, error
    """
    api_key = fal_api_key()
    model_key, endpoint = _resolve_endpoint(model)
    image_size = size or PORTRAIT_SIZE
    meta: dict = {
        "model": model_key,
        "endpoint": endpoint,
        "cost_usd": 0.0,
        "cached": False,
        "source": "failed",
    }

    if not api_key:
        meta["error"] = "FAL_KEY not set"
        return None, meta

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    dest.parent.mkdir(parents=True, exist_ok=True)
    cache_file = _cache_path(prompt, model_key, image_size, cache_namespace)

    if use_cache and cache_file.exists() and cache_file.stat().st_size > 1000:
        import shutil
        shutil.copy2(cache_file, dest)
        meta.update(source="cache", cached=True, cost_usd=0.0)
        return dest, meta

    url = f"https://fal.run/{endpoint}"
    headers = {"Authorization": f"Key {api_key}", "Content-Type": "application/json"}
    body = {
        "prompt": prompt,
        "image_size": image_size,
        "num_images": 1,
    }

    last_error = ""
    for attempt in range(max_retries + 1):
        try:
            response = httpx.post(url, headers=headers, json=body, timeout=120)
            response.raise_for_status()
            payload = response.json()
            image_url = _extract_image_url(payload)
            if not image_url:
                last_error = "No image URL in fal response"
                continue

            data = _download_image_bytes(image_url)
            if not data:
                last_error = "Failed to download fal image"
                continue

            if len(data) < 1000:
                last_error = "Downloaded image too small"
                continue

            dest.write_bytes(data)
            import shutil
            shutil.copy2(dest, cache_file)
            meta.update(
                source="api",
                cached=False,
                cost_usd=estimate_cost(model_key, 1),
            )
            return dest, meta
        except Exception as exc:
            last_error = str(exc)
            if attempt < max_retries:
                time.sleep(1.5 * (attempt + 1))

    meta["error"] = last_error
    print(f"   fal.ai image failed ({model_key}): {last_error}")
    return None, meta


def _cutout_cache_path(image_path: Path) -> Path:
    digest = hashlib.sha256(image_path.read_bytes()).hexdigest()[:20]
    return CUTOUT_CACHE_DIR / f"{digest}.png"


def _upload_local_image(path: Path, api_key: str) -> str | None:
    """Upload a local image to fal storage; returns a public URL."""
    try:
        with path.open("rb") as handle:
            response = httpx.post(
                "https://fal.run/storage/upload",
                headers={"Authorization": f"Key {api_key}"},
                files={"file": (path.name, handle, "image/png")},
                timeout=90,
            )
        response.raise_for_status()
        payload = response.json()
        url = payload.get("url") or payload.get("file_url")
        if url:
            return url
    except Exception:
        pass

    try:
        encoded = base64.b64encode(path.read_bytes()).decode()
        return f"data:image/png;base64,{encoded}"
    except Exception:
        return None


def remove_background(
    image_path: Path,
    *,
    dest: Path,
    model: str = "light",
    use_cache: bool = True,
) -> tuple[Path | None, dict]:
    """
    Remove background via fal-ai/birefnet/v2 (General Use Light by default).
    Returns (path, meta) with cost_usd estimate.
    """
    api_key = fal_api_key()
    model_label = "General Use (Light)" if model == "light" else "General Use (Heavy)"
    meta: dict = {
        "model": "birefnet-light",
        "endpoint": BIREFNET_ENDPOINT,
        "cost_usd": 0.0,
        "cached": False,
        "source": "failed",
    }

    if not api_key:
        meta["error"] = "FAL_KEY not set"
        return None, meta

    if not image_path.exists() or image_path.stat().st_size < 500:
        meta["error"] = "source frame missing"
        return None, meta

    CUTOUT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    dest.parent.mkdir(parents=True, exist_ok=True)
    cache_file = _cutout_cache_path(image_path)

    if use_cache and cache_file.exists() and cache_file.stat().st_size > 500:
        import shutil
        shutil.copy2(cache_file, dest)
        meta.update(source="cache", cached=True, cost_usd=0.0)
        return dest, meta

    image_url = _upload_local_image(image_path, api_key)
    if not image_url:
        meta["error"] = "failed to stage image for cutout"
        return None, meta

    url = f"https://fal.run/{BIREFNET_ENDPOINT}"
    headers = {"Authorization": f"Key {api_key}", "Content-Type": "application/json"}
    body = {
        "image_url": image_url,
        "model": model_label,
        "operating_resolution": "1024x1024",
        "refine_foreground": True,
        "output_format": "png",
    }

    try:
        response = httpx.post(url, headers=headers, json=body, timeout=120)
        response.raise_for_status()
        payload = response.json()
        out_url = _extract_image_url(payload)
        if not out_url:
            meta["error"] = "No cutout URL in fal response"
            return None, meta

        data = _download_image_bytes(out_url)
        if not data or len(data) < 500:
            meta["error"] = "Failed to download cutout"
            return None, meta

        dest.write_bytes(data)
        import shutil
        shutil.copy2(dest, cache_file)
        meta.update(
            source="api",
            cached=False,
            cost_usd=MODEL_COST_USD.get("birefnet-light", 0.008),
        )
        return dest, meta
    except Exception as exc:
        meta["error"] = str(exc)
        print(f"   fal.ai cutout failed: {exc}")
        return None, meta
