from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from src.pipeline_config import jump_cut_max_remove_ratio, jump_cut_min_silence

MIN_SILENCE_S = 0.15
MAX_REMOVE_RATIO = 0.35


def _run_ffmpeg(args: list[str]) -> str:
    result = subprocess.run(
        ["ffmpeg", *args],
        capture_output=True,
        text=True,
    )
    return result.stderr + result.stdout


def _loudnorm_threshold(video_path: Path) -> float:
    out = _run_ffmpeg([
        "-i", str(video_path),
        "-map", "0:a",
        "-af", "loudnorm=print_format=json",
        "-f", "null", "-",
    ])
    match = re.search(r'"input_thresh"\s*:\s*"([^"]+)"', out)
    if match:
        return float(match.group(1))
    return -40.0


def detect(
    video_path: Path,
    min_silence: float | None = None,
    max_remove_ratio: float | None = None,
    preferred_pause_seconds: list[float] | None = None,
) -> dict:
    min_silence = min_silence if min_silence is not None else jump_cut_min_silence()
    max_remove_ratio = (
        max_remove_ratio if max_remove_ratio is not None else jump_cut_max_remove_ratio()
    )
    thresh = _loudnorm_threshold(video_path)
    out = _run_ffmpeg([
        "-i", str(video_path),
        "-map", "0:a",
        "-af", f"silencedetect=noise={thresh}dB:d={min_silence}",
        "-f", "null", "-",
    ])

    silences: list[tuple[float, float]] = []
    starts: list[float] = []
    for line in out.splitlines():
        if "silence_start:" in line:
            m = re.search(r"silence_start:\s*([\d.]+)", line)
            if m:
                starts.append(float(m.group(1)))
        if "silence_end:" in line and starts:
            m = re.search(r"silence_end:\s*([\d.]+)", line)
            if m:
                silences.append((starts.pop(0), float(m.group(1))))

    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)],
        capture_output=True,
        text=True,
        check=True,
    )
    duration = float(probe.stdout.strip() or 0)

    if silences and silences[-1][1] >= duration - 0.05 and not starts:
        pass
    elif starts:
        silences.append((starts[0], duration))

    removed = sum(e - s for s, e in silences)
    if duration > 0 and removed / duration > max_remove_ratio:
        silences = []
        removed = 0

    # Prefer cutting near script recording_cues PAUSE targets (±0.4s)
    if preferred_pause_seconds and silences:
        tuned: list[tuple[float, float]] = []
        for s, e in silences:
            mid = (s + e) / 2
            best = min(preferred_pause_seconds, key=lambda t: abs(t - mid), default=None)
            if best is not None and abs(best - mid) <= 0.4:
                pad = min(0.08, (e - s) / 4)
                tuned.append((max(s, best - pad), min(e, best + pad)))
            else:
                tuned.append((s, e))
        silences = tuned
        removed = sum(e - s for s, e in silences)

    kept: list[dict] = []
    cursor = 0.0
    for s, e in silences:
        if s > cursor + 0.05:
            kept.append({"start_s": round(cursor, 3), "end_s": round(s, 3)})
        cursor = e
    if cursor < duration - 0.05:
        kept.append({"start_s": round(cursor, 3), "end_s": round(duration, 3)})

    if not kept:
        kept = [{"start_s": 0.0, "end_s": round(duration, 3)}]

    return {
        "silences": [{"start_s": round(s, 3), "end_s": round(e, 3)} for s, e in silences],
        "kept_segments": kept,
        "removed_total_s": round(removed, 3),
        "original_duration_s": round(duration, 3),
    }


def save(result: dict, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2))
    return path
