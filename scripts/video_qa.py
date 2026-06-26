#!/usr/bin/env python3
"""
Extract frames at pipeline moment timestamps and optionally score with Claude vision.

Usage:
  python scripts/video_qa.py projects/script_01_cursor_is_worth_the/final.mp4
  python scripts/video_qa.py projects/script_01_cursor_is_worth_the/final.mp4 --vision
"""

from __future__ import annotations

import argparse
import hashlib
import base64
import json
import subprocess
import sys
from pathlib import Path

ENGINE_ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ENGINE_ROOT / "remotion" / "public"


def _load_moments() -> list[dict]:
    moments: list[dict] = []
    broll_path = PUBLIC / "broll_moments.json"
    social_path = PUBLIC / "social_moments.json"
    fps = 30.0
    transcript_path = PUBLIC / "transcript.json"
    if transcript_path.exists():
        fps = float(json.loads(transcript_path.read_text()).get("fps", 30))

    if broll_path.exists():
        data = json.loads(broll_path.read_text())
        for m in data.get("moments", []):
            mid = (m["start_frame"] + m["end_frame"]) / 2 / fps
            moments.append({
                "label": f"broll:{m.get('layout', '?')}:{m.get('keyword', '')}",
                "seconds": round(mid, 2),
                "frame": m["start_frame"],
            })

    if social_path.exists():
        data = json.loads(social_path.read_text())
        for m in data.get("moments", []):
            mid = (m["start_frame"] + m["end_frame"]) / 2 / fps
            moments.append({
                "label": f"social:{m.get('type', '?')}",
                "seconds": round(mid, 2),
                "frame": m["start_frame"],
            })

    hook = {"label": "hook:0s", "seconds": 0.0, "frame": 0}
    return [hook] + sorted(moments, key=lambda x: x["seconds"])


def _probe_audio(video: Path) -> bool:
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "a:0",
        "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(video),
    ]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=20)
        return "audio" in (out.stdout or "").lower()
    except Exception:
        return False


def _black_ratio(image: Path) -> float:
    try:
        from PIL import Image
    except ImportError:
        return 0.0
    img = Image.open(image).convert("L")
    pixels = list(img.getdata())
    dark = sum(1 for p in pixels if p < 12)
    return dark / max(len(pixels), 1)


def extract_frame(video: Path, seconds: float, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-ss", str(seconds),
        "-i", str(video), "-frames:v", "1", "-q:v", "2", str(dest),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=30)
        return dest.exists()
    except Exception:
        return False


def vision_review(frames: list[Path]) -> str:
    import os
    import httpx

    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return "ANTHROPIC_API_KEY not set — skipping vision review."

    content: list[dict] = [{
        "type": "text",
        "text": (
            "You are a short-form video QA editor. For each frame, score 1-10 and list issues: "
            "lip-sync, cropping, overlay clutter, text blocking face, compositing seams, "
            "distracting flashes, readability. Be blunt and specific."
        ),
    }]
    for path in frames:
        data = base64.standard_b64encode(path.read_bytes()).decode()
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": data,
            },
        })
        content.append({"type": "text", "text": f"Frame: {path.stem}"})

    response = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 1200,
            "messages": [{"role": "user", "content": content}],
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["content"][0]["text"]


def _assert_broll_unique() -> bool:
    broll_path = PUBLIC / "broll_moments.json"
    if not broll_path.exists():
        return True
    data = json.loads(broll_path.read_text())
    digests: dict[str, list[str]] = {}
    for m in data.get("moments", []):
        rel = m.get("image_file")
        if not rel:
            continue
        img = PUBLIC / rel
        if not img.exists():
            continue
        digest = hashlib.md5(img.read_bytes()).hexdigest()
        digests.setdefault(digest, []).append(m.get("keyword", rel))
    dupes = {d: kws for d, kws in digests.items() if len(kws) > 1}
    if dupes:
        for digest, kws in dupes.items():
            print(f"ASSERT FAIL: duplicate b-roll image for {kws}", file=sys.stderr)
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Video QA frame extraction + optional vision")
    parser.add_argument("video", type=Path, help="Path to final.mp4")
    parser.add_argument("--vision", action="store_true", help="Send frames to Claude vision")
    parser.add_argument("--out", type=Path, default=None, help="Output directory for frames")
    parser.add_argument("--assert-audio-present", action="store_true")
    parser.add_argument("--assert-no-black-frames", action="store_true")
    parser.add_argument("--assert-broll-unique", action="store_true")
    args = parser.parse_args()

    video = args.video.resolve()
    if not video.exists():
        print(f"Video not found: {video}", file=sys.stderr)
        return 1

    out_dir = args.out or (video.parent / "qa_frames")
    moments = _load_moments()
    extracted: list[Path] = []

    print(f"QA: {video.name} → {out_dir}")
    for m in moments:
        dest = out_dir / f"{m['seconds']:05.2f}s_{m['label'].replace(':', '_')}.jpg"
        ok = extract_frame(video, m["seconds"], dest)
        status = "ok" if ok else "FAIL"
        print(f"  [{status}] {m['seconds']:5.2f}s  {m['label']}")
        if ok:
            extracted.append(dest)

    report_path = out_dir / "qa_report.txt"
    lines = [f"Video: {video}", f"Frames extracted: {len(extracted)}", ""]

    if args.vision and extracted:
        print("\nRunning Claude vision review...")
        try:
            review = vision_review(extracted)
            lines.append(review)
            print(review)
        except Exception as exc:
            lines.append(f"Vision review failed: {exc}")
            print(f"Vision review failed: {exc}", file=sys.stderr)
    elif args.vision:
        lines.append("No frames extracted for vision review.")

    if args.assert_audio_present and not _probe_audio(video):
        print("ASSERT FAIL: no audio stream in video", file=sys.stderr)
        return 1

    black_failures = 0
    if args.assert_no_black_frames:
        for frame_path in extracted:
            if _black_ratio(frame_path) > 0.92:
                black_failures += 1
                print(f"ASSERT FAIL: near-black frame {frame_path.name}", file=sys.stderr)
        if black_failures:
            return 1

    if args.assert_broll_unique and not _assert_broll_unique():
        return 1

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReport: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
