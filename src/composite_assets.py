from __future__ import annotations

import subprocess
from pathlib import Path

from src import fal_client
from src.pipeline_config import ai_cutout_max_per_video, ai_cutout_model, ai_images_enabled

ENGINE_ROOT = Path(__file__).resolve().parent.parent
PUBLIC_DIR = ENGINE_ROOT / "remotion" / "public"
CUTOUTS_DIR = PUBLIC_DIR / "ai_images" / "cutouts"
FRAMES_DIR = PUBLIC_DIR / "ai_images" / "frames"


def extract_keyframe(video_path: Path, frame: int, fps: float, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    timestamp = max(0.0, frame / fps)
    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        f"{timestamp:.3f}",
        "-i",
        str(video_path),
        "-frames:v",
        "1",
        "-q:v",
        "2",
        str(dest),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=60)
        return dest.exists() and dest.stat().st_size > 500
    except Exception as exc:
        print(f"   Keyframe extract failed (frame {frame}): {exc}")
        return False


def fill_cutouts(
    broll_result: dict,
    video_path: Path,
    transcript: dict,
) -> dict:
    """
    Generate presenter cutouts for moments with layout=presenter_cutout.
    Falls back to presenter_on_bg when cutout budget is exhausted or API fails.
    """
    summary = {
        "generated": 0,
        "cached": 0,
        "failed": 0,
        "skipped": 0,
        "cost_usd": 0.0,
    }

    if not ai_images_enabled():
        return summary

    fps = float(transcript.get("fps", 30))
    budget = ai_cutout_max_per_video()
    model = ai_cutout_model()
    used = 0

    for moment in broll_result.get("moments", []):
        if moment.get("layout") != "presenter_cutout":
            continue
        if used >= budget:
            moment["layout"] = "presenter_on_bg"
            summary["skipped"] += 1
            continue

        frame = int(moment.get("start_frame", 0))
        frame_path = FRAMES_DIR / f"frame_{frame}.png"
        if not frame_path.exists():
            if not extract_keyframe(video_path, frame, fps, frame_path):
                moment["layout"] = "presenter_on_bg"
                summary["failed"] += 1
                continue

        rel = f"ai_images/cutouts/cutout_{frame}.png"
        dest = PUBLIC_DIR / rel
        path, meta = fal_client.remove_background(frame_path, dest=dest, model=model)
        used += 1

        if path:
            moment["cutout_file"] = rel
            moment["layout"] = "presenter_cutout"
            if meta.get("cached"):
                summary["cached"] += 1
            else:
                summary["generated"] += 1
            summary["cost_usd"] = round(summary["cost_usd"] + float(meta.get("cost_usd", 0)), 4)
        else:
            moment["layout"] = "presenter_on_bg"
            summary["failed"] += 1

    if summary["generated"] or summary["cached"]:
        print(
            f"   AI cutouts: {summary['generated']} generated, {summary['cached']} cached, "
            f"${summary['cost_usd']:.3f} est."
        )
    return summary
