from __future__ import annotations

"""
Score transcript windows for standalone clip extraction.
Usage: python -m src.hook_extractor --transcript remotion/public/transcript.json --count 10
"""

import argparse
import json
import re
from pathlib import Path

HOOK_PHRASES = [
    "break it down",
    "here's how",
    "here is how",
    "the truth is",
    "what if",
    "stop doing",
    "biggest mistake",
    "nobody tells you",
]

FPS = 30
MIN_CLIP_FRAMES = 20 * FPS
MAX_CLIP_FRAMES = 45 * FPS


def _score_window(words: list, start_idx: int, end_idx: int, full_text: str) -> float:
    chunk = " ".join(w["word"] for w in words[start_idx:end_idx]).lower()
    score = 0.0
    for phrase in HOOK_PHRASES:
        if phrase in chunk:
            score += 3.0
    if re.search(r"\b\d+\b", chunk):
        score += 1.5
    if "?" in chunk:
        score += 1.0
    word_count = end_idx - start_idx
    if 15 <= word_count <= 80:
        score += 1.0
    if start_idx < len(words) * 0.15:
        score += 0.5
    return score


def extract(transcript: dict, count: int = 10) -> dict:
    words = transcript.get("words", [])
    total = transcript.get("total_frames", 0)
    full_text = transcript.get("full_text", "")

    candidates: list[dict] = []
    for start_idx in range(0, max(len(words) - 10, 1), 5):
        for duration_words in range(20, 90, 10):
            end_idx = min(start_idx + duration_words, len(words))
            if end_idx - start_idx < 12:
                continue
            start_frame = words[start_idx]["start_frame"]
            end_frame = words[end_idx - 1]["end_frame"]
            clip_frames = end_frame - start_frame
            if clip_frames < MIN_CLIP_FRAMES or clip_frames > MAX_CLIP_FRAMES:
                continue
            score = _score_window(words, start_idx, end_idx, full_text)
            if score < 2:
                continue
            hook_text = " ".join(w["word"] for w in words[start_idx : start_idx + 8])
            candidates.append({
                "start_frame": start_frame,
                "end_frame": end_frame,
                "score": round(score, 2),
                "hook_text": hook_text[:80],
                "duration_s": round(clip_frames / FPS, 1),
            })

    candidates.sort(key=lambda c: c["score"], reverse=True)
    accepted: list[dict] = []
    for c in candidates:
        if any(abs(c["start_frame"] - a["start_frame"]) < 90 for a in accepted):
            continue
        accepted.append(c)
        if len(accepted) >= count:
            break

    return {
        "clips": accepted,
        "summary": {"candidates": len(candidates), "selected": len(accepted)},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--transcript", required=True)
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    transcript = json.loads(Path(args.transcript).read_text())
    result = extract(transcript, args.count)
    out = Path(args.out) if args.out else Path(args.transcript).parent / "clips_manifest.json"
    out.write_text(json.dumps(result, indent=2))
    print(f"Extracted {result['summary']['selected']} clips → {out}")


if __name__ == "__main__":
    main()
