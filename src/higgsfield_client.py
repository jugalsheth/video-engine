"""Higgsfield CLI client for automated hook-hero stills.

One-time setup (on the machine that runs video-engine):
  1. npm i -g @higgsfield/cli   OR   brew install higgsfield-ai/tap/higgsfield
  2. higgsfield auth login      # browser once; stores ~/.config/higgsfield/credentials.json

Env:
  HIGGSFIELD_ENABLED=true|false   (default: true if CLI present)
  HIGGSFIELD_MODEL=nano_banana_2  (cheap/fast still; override for quality)
  HIGGSFIELD_CLI=higgsfield       (path to binary)
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from urllib.request import urlretrieve

import httpx

DEFAULT_MODEL = "nano_banana_2_lite"  # 1 credit — good quality, cheapest still
URL_RE = re.compile(r"https?://[^\s\"']+")


def cli_path() -> str | None:
    configured = os.getenv("HIGGSFIELD_CLI", "higgsfield").strip()
    return shutil.which(configured)


def higgsfield_enabled() -> bool:
    flag = os.getenv("HIGGSFIELD_ENABLED", "").lower()
    if flag in ("0", "false", "no", "off"):
        return False
    if flag in ("1", "true", "yes", "on"):
        return True
    return cli_path() is not None


def model_name() -> str:
    return os.getenv("HIGGSFIELD_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL


def _extract_url(payload: object) -> str | None:
    if isinstance(payload, str):
        m = URL_RE.search(payload)
        return m.group(0).rstrip(".,)") if m else None
    if isinstance(payload, dict):
        for key in ("url", "image_url", "result_url", "output_url", "media_url"):
            val = payload.get(key)
            if isinstance(val, str) and val.startswith("http"):
                return val
        for key in ("images", "outputs", "results", "media"):
            items = payload.get(key)
            if isinstance(items, list) and items:
                found = _extract_url(items[0])
                if found:
                    return found
        for val in payload.values():
            found = _extract_url(val)
            if found:
                return found
    if isinstance(payload, list):
        for item in payload:
            found = _extract_url(item)
            if found:
                return found
    return None


def _download(url: str, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with httpx.stream("GET", url, timeout=120.0, follow_redirects=True) as resp:
            resp.raise_for_status()
            with dest.open("wb") as f:
                for chunk in resp.iter_bytes():
                    f.write(chunk)
        return dest.exists() and dest.stat().st_size > 500
    except Exception:
        try:
            urlretrieve(url, dest)
            return dest.exists() and dest.stat().st_size > 500
        except Exception as exc:
            print(f"   ⚠️ Higgsfield download failed: {exc}")
            return False


def generate_still(prompt: str, dest: Path, *, aspect_ratio: str = "9:16") -> dict:
    """Run higgsfield generate create --wait --json and save image to dest."""
    meta: dict = {
        "ok": False,
        "path": None,
        "model": model_name(),
        "url": None,
        "error": None,
        "raw": None,
    }
    binary = cli_path()
    if not binary:
        meta["error"] = "higgsfield CLI not found — npm i -g @higgsfield/cli && higgsfield auth login"
        return meta

    cmd = [
        binary,
        "generate",
        "create",
        model_name(),
        "--prompt",
        prompt,
        "--aspect_ratio",
        aspect_ratio,
        "--wait",
        "--json",
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
    except subprocess.TimeoutExpired:
        meta["error"] = "higgsfield CLI timed out"
        return meta
    except FileNotFoundError:
        meta["error"] = "higgsfield CLI not found"
        return meta

    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()
    meta["raw"] = stdout[:2000] if stdout else stderr[:500]

    if proc.returncode != 0:
        meta["error"] = stderr or stdout or f"exit {proc.returncode}"
        if "Session expired" in meta["error"] or "auth" in meta["error"].lower():
            meta["error"] += " — run: higgsfield auth login"
        return meta

    url = None
    try:
        parsed = json.loads(stdout)
        url = _extract_url(parsed)
    except json.JSONDecodeError:
        url = _extract_url(stdout)

    if not url:
        meta["error"] = "CLI succeeded but no media URL in output"
        return meta

    meta["url"] = url
    if not _download(url, dest):
        meta["error"] = "failed to download generated image"
        return meta

    meta["ok"] = True
    meta["path"] = dest
    return meta
