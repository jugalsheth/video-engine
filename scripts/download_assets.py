#!/usr/bin/env python3
"""
One-time downloader for CC0 SFX and music assets.
Run from video-engine/: python scripts/download_assets.py

Sources (CC0 / free license):
- SFX: generated via ffmpeg (Mixkit-style tones) when URLs unavailable
- Music: Pixabay audio API if PIXABAY_API_KEY set, else ffmpeg ambient bed
- Lottie: minimal pulse animations committed to public/lottie/
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import httpx

ENGINE_ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ENGINE_ROOT / "remotion" / "public"
SFX_DIR = PUBLIC / "sfx"
MUSIC_DIR = PUBLIC / "music"
LOTTIE_DIR = PUBLIC / "lottie"

# Mixkit CC0 direct links (may change; ffmpeg fallback if 404)
MIXKIT_URLS = {
    "whoosh.wav": "https://assets.mixkit.co/active_storage/sfx/2571/2571-preview.mp3",
    "pop.wav": "https://assets.mixkit.co/active_storage/sfx/2568/2568-preview.mp3",
    "tick.wav": "https://assets.mixkit.co/active_storage/sfx/2572/2572-preview.mp3",
    "swoosh.wav": "https://assets.mixkit.co/active_storage/sfx/2570/2570-preview.mp3",
    "impact.wav": "https://assets.mixkit.co/active_storage/sfx/2567/2567-preview.mp3",
}


def _ffmpeg(args: list[str]) -> None:
    subprocess.run(["ffmpeg", *args], capture_output=True, check=True)


def _download_or_generate(name: str, url: str, dest: Path, gen_args: list[str]) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".tmp")
    try:
        r = httpx.get(url, timeout=30, follow_redirects=True)
        if r.status_code == 200 and len(r.content) > 500:
            tmp.write_bytes(r.content)
            _ffmpeg(["-i", str(tmp), "-y", str(dest)])
            tmp.unlink(missing_ok=True)
            print(f"  ✓ {name} (downloaded)")
            return
    except Exception:
        pass
    _ffmpeg(gen_args)
    print(f"  ✓ {name} (generated)")


def download_sfx() -> None:
    print("SFX:")
    specs = {
        "whoosh.wav": [
            "-f", "lavfi", "-i", "sine=frequency=800:duration=0.3",
            "-af", "afade=t=out:st=0.1:d=0.2,volume=0.5",
            "-y", str(SFX_DIR / "whoosh.wav"),
        ],
        "pop.wav": [
            "-f", "lavfi", "-i", "sine=frequency=1200:duration=0.08",
            "-af", "volume=0.6",
            "-y", str(SFX_DIR / "pop.wav"),
        ],
        "tick.wav": [
            "-f", "lavfi", "-i", "sine=frequency=2000:duration=0.05",
            "-af", "volume=0.4",
            "-y", str(SFX_DIR / "tick.wav"),
        ],
        "swoosh.wav": [
            "-f", "lavfi", "-i", "sine=frequency=400:duration=0.4",
            "-af", "afade=t=out:st=0.15:d=0.25,volume=0.45",
            "-y", str(SFX_DIR / "swoosh.wav"),
        ],
        "impact.wav": [
            "-f", "lavfi", "-i", "sine=frequency=80:duration=0.25",
            "-af", "volume=0.7,lowpass=f=200",
            "-y", str(SFX_DIR / "impact.wav"),
        ],
    }
    for name, gen_args in specs.items():
        dest = SFX_DIR / name
        if dest.exists() and dest.stat().st_size > 500:
            print(f"  · {name} (exists)")
            continue
        url = MIXKIT_URLS.get(name, "")
        _download_or_generate(name, url, dest, gen_args)


def _pixabay_music(query: str, dest: Path, key: str) -> bool:
    try:
        r = httpx.get(
            "https://pixabay.com/api/",
            params={"key": key, "q": query, "audio_type": "music", "per_page": 5},
            timeout=15,
        )
        for hit in r.json().get("hits", []):
            url = hit.get("previewURL") or hit.get("audio")
            if url:
                dest.write_bytes(httpx.get(url, timeout=60).content)
                if dest.stat().st_size > 5000:
                    return True
    except Exception:
        pass
    return False


def _generated_bed(dest: Path, freqs: list[int], tempo: str = "slow") -> None:
    duration = 45
    inputs = []
    for i, f in enumerate(freqs):
        inputs.extend(["-f", "lavfi", "-i", f"sine=frequency={f}:duration={duration}"])
    n = len(freqs)
    mix = "".join(f"[{i}]" for i in range(n)) + f"amix=inputs={n}:duration=first,volume=0.12"
    if tempo == "mid":
        mix += ",atempo=1.05"
    elif tempo == "fast":
        mix += ",atempo=1.12"
    _ffmpeg([
        *inputs,
        "-filter_complex", mix,
        "-c:a", "libmp3lame", "-b:a", "128k",
        "-y", str(dest),
    ])


def download_music() -> None:
    print("Music:")
    MUSIC_DIR.mkdir(parents=True, exist_ok=True)

    from dotenv import load_dotenv
    import os

    load_dotenv(ENGINE_ROOT.parent / ".env")
    load_dotenv(ENGINE_ROOT / ".env")
    key = os.getenv("PIXABAY_API_KEY", "")

    library_path = ENGINE_ROOT / "rules" / "music_library.json"
    specs = {
        "calm_lofi.mp3": (["lofi ambient", "chill hip hop instrumental"], [220, 330], "slow"),
        "mid_beat.mp3": (["motivational beat instrumental", "corporate upbeat no vocals"], [180, 270, 360], "mid"),
        "hype_energy.mp3": (["phonk instrumental", "trap beat no vocals"], [110, 165, 220], "fast"),
    }

    legacy = MUSIC_DIR / "background.mp3"
    for filename, (queries, freqs, tempo) in specs.items():
        dest = MUSIC_DIR / filename
        if dest.exists() and dest.stat().st_size > 5000:
            print(f"  · {filename} (exists)")
            continue
        if key and any(_pixabay_music(q, dest, key) for q in queries):
            print(f"  ✓ {filename} (Pixabay)")
            continue
        if legacy.exists() and legacy.stat().st_size > 5000 and filename == "calm_lofi.mp3":
            dest.write_bytes(legacy.read_bytes())
            print(f"  ✓ {filename} (copied legacy)")
            continue
        _generated_bed(dest, freqs, tempo)
        print(f"  ✓ {filename} (generated)")

    if not legacy.exists() or legacy.stat().st_size <= 5000:
        calm = MUSIC_DIR / "calm_lofi.mp3"
        if calm.exists():
            legacy.write_bytes(calm.read_bytes())
            print("  ✓ background.mp3 (alias of calm_lofi)")


def write_lottie_files() -> None:
    print("Lottie:")
    LOTTIE_DIR.mkdir(parents=True, exist_ok=True)

    pulse = {
        "v": "5.7.4",
        "fr": 30,
        "ip": 0,
        "op": 60,
        "w": 120,
        "h": 120,
        "layers": [
            {
                "ty": 4,
                "nm": "pulse",
                "sr": 1,
                "ks": {
                    "o": {"a": 0, "k": 100},
                    "r": {"a": 0, "k": 0},
                    "p": {"a": 0, "k": [60, 60, 0]},
                    "a": {"a": 0, "k": [0, 0, 0]},
                    "s": {
                        "a": 1,
                        "k": [
                            {"t": 0, "s": [70, 70, 100]},
                            {"t": 30, "s": [110, 110, 100]},
                            {"t": 60, "s": [70, 70, 100]},
                        ],
                    },
                },
                "shapes": [
                    {"ty": "el", "p": {"a": 0, "k": [0, 0]}, "s": {"a": 0, "k": [50, 50]}},
                    {"ty": "fl", "c": {"a": 0, "k": [0.79, 0.57, 0.23, 1]}, "o": {"a": 0, "k": 100}},
                ],
                "ip": 0,
                "op": 60,
                "st": 0,
            }
        ],
    }

    for name in ("chart_growth.json", "checkmark.json", "data_pulse.json"):
        path = LOTTIE_DIR / name
        path.write_text(json.dumps(pulse, indent=2))
        print(f"  ✓ {name}")


def _lottie_burst(color: list[float]) -> dict:
    layers = []
    for i in range(8):
        angle = i * 45
        layers.append({
            "ty": 4,
            "nm": f"particle_{i}",
            "sr": 1,
            "ks": {
                "o": {"a": 1, "k": [{"t": 0, "s": [100]}, {"t": 45, "s": [0]}]},
                "r": {"a": 0, "k": angle},
                "p": {
                    "a": 1,
                    "k": [
                        {"t": 0, "s": [60, 60, 0]},
                        {"t": 45, "s": [60 + 50, 60 - 40, 0]},
                    ],
                },
                "a": {"a": 0, "k": [0, 0, 0]},
                "s": {"a": 0, "k": [100, 100, 100]},
            },
            "shapes": [
                {"ty": "el", "p": {"a": 0, "k": [0, 0]}, "s": {"a": 0, "k": [12, 12]}},
                {"ty": "fl", "c": {"a": 0, "k": color}, "o": {"a": 0, "k": 100}},
            ],
            "ip": 0,
            "op": 60,
            "st": 0,
        })
    return {"v": "5.7.4", "fr": 30, "ip": 0, "op": 60, "w": 120, "h": 120, "layers": layers}


def write_fun_lottie_files() -> None:
    print("Fun Lottie:")
    fun_dir = LOTTIE_DIR / "fun"
    fun_dir.mkdir(parents=True, exist_ok=True)
    specs = {
        "confetti.json": [1, 0.84, 0, 1],
        "money_rain.json": [0.2, 0.8, 0.3, 1],
        "fire_spark.json": [1, 0.4, 0.1, 1],
        "mind_blown.json": [0, 0.83, 1, 1],
    }
    for name, color in specs.items():
        path = fun_dir / name
        path.write_text(json.dumps(_lottie_burst(color), indent=2))
        print(f"  ✓ fun/{name}")


def main() -> int:
    print(f"Asset dir: {PUBLIC}\n")
    download_sfx()
    download_music()
    write_lottie_files()
    write_fun_lottie_files()
    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
