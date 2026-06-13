"""Tests for custom visual override shot planning."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

VIDEO_ENGINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(VIDEO_ENGINE))

from src.shot_planner import _custom_visual_shots  # noqa: E402


class TestCustomVisualShots(unittest.TestCase):
    def test_custom_visual_matches_trigger_phrase(self):
        words = []
        text = "this is where the deduplication happened in our pipeline"
        for i, w in enumerate(text.split()):
            words.append({
                "word": w,
                "start_frame": i * 10,
                "end_frame": i * 10 + 8,
            })
        transcript = {
            "full_text": text,
            "words": words,
            "total_frames": 300,
        }
        script = {
            "filename_hint": "script_01_dedup.mp4",
            "custom_visual_overrides": [{
                "trigger_phrase": "deduplication happened",
                "description": "before/after schema diagram",
                "asset_status": "needs_creation",
            }],
        }
        shots, reserved = _custom_visual_shots(script, transcript)
        self.assertEqual(len(shots), 1)
        self.assertEqual(shots[0]["type"], "CUSTOM_VISUAL")
        self.assertGreater(len(reserved), 0)


if __name__ == "__main__":
    unittest.main()
