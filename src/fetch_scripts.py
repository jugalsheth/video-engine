"""
Fetches the latest scripts_archive.json directly from GitHub.
No git clone needed. No manual copy-paste.
Uses the raw GitHub URL — always gets the latest committed version.
Falls back to local cache if GitHub is unreachable.
"""

import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path

import httpx

ENGINE_ROOT = Path(__file__).resolve().parent.parent
ARCHIVE_PATH = ENGINE_ROOT / "data" / "scripts_archive.json"
ARCHIVE_URL = os.getenv("SCRIPTS_ARCHIVE_URL")


def fetch_latest() -> list:
    """
    Fetches scripts archive from GitHub raw URL.
    Returns list of script objects.
    Falls back to cached local file if fetch fails.
    """
    ARCHIVE_PATH.parent.mkdir(exist_ok=True)

    if not ARCHIVE_URL:
        print("   SCRIPTS_ARCHIVE_URL not set — using local cache only")

    if ARCHIVE_URL:
        try:
            response = httpx.get(ARCHIVE_URL, timeout=10)
            response.raise_for_status()
            scripts = response.json()

            ARCHIVE_PATH.write_text(json.dumps(scripts, indent=2))
            print(f"   Fetched {len(scripts)} scripts from GitHub")
            return scripts

        except Exception as e:
            print(f"   GitHub fetch failed: {e}")
            print("   Falling back to local cache...")

    try:
        scripts = json.loads(ARCHIVE_PATH.read_text())
        print(f"   Loaded {len(scripts)} scripts from local cache")
        return scripts
    except Exception:
        print("   No local cache found. Continuing without scripts.")
        return []


def get_recent(days: int = 7) -> list:
    """
    Returns only scripts generated in the last N days.
    Useful for matching — only look at recent scripts.
    """
    scripts = fetch_latest()
    if not scripts:
        return []

    cutoff = (date.today() - timedelta(days=days)).isoformat()
    recent = [s for s in scripts if s.get("date_generated", "") >= cutoff]
    print(f"   {len(recent)} scripts from last {days} days")
    return recent
