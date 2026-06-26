"""Tests for project folders and asset auto-matching."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

VIDEO_ENGINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(VIDEO_ENGINE))

from src.asset_matcher import resolve_overrides  # noqa: E402
from src.frame_utils import frame_for_step_number  # noqa: E402
from src.project_paths import slugify  # noqa: E402


class TestSlugify(unittest.TestCase):
    def test_filename_hint(self):
        self.assertEqual(slugify("script_03_kafka_hiring.mp4"), "script_03_kafka_hiring")

    def test_spaces_and_caps(self):
        self.assertEqual(
            slugify("script_1_DATA ENGINEERS ARE RECESSION-PROOF.mp4"),
            "script_1_data_engineers_are_recession_proof",
        )


class TestAssetMatcher(unittest.TestCase):
    def test_matches_trigger_slug_in_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            assets = Path(tmp)
            (assets / "deduplication_happened.png").write_bytes(b"png")

            script = {
                "custom_visual_overrides": [{
                    "trigger_phrase": "deduplication happened",
                    "description": "diagram",
                    "asset_status": "needs_creation",
                }],
            }
            updated, matched = resolve_overrides(script, assets)
            self.assertEqual(matched, ["deduplication_happened.png"])
            self.assertEqual(updated["custom_visual_overrides"][0]["asset_status"], "ready")

    def test_single_asset_single_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            assets = Path(tmp)
            (assets / "screenshot.png").write_bytes(b"png")

            script = {
                "custom_visual_overrides": [{
                    "trigger_phrase": "something else entirely",
                    "asset_status": "needs_creation",
                }],
            }
            updated, matched = resolve_overrides(script, assets)
            self.assertEqual(len(matched), 1)
            self.assertEqual(updated["custom_visual_overrides"][0]["asset_status"], "ready")


class TestStepFrameTiming(unittest.TestCase):
    def test_frame_for_step_number_uses_number_word(self):
        words = [
            {"word": "Step", "start_frame": 100, "end_frame": 105},
            {"word": "1.", "start_frame": 106, "end_frame": 112},
            {"word": "Learn", "start_frame": 130, "end_frame": 140},
        ]
        self.assertEqual(frame_for_step_number(words, 1), 106)


if __name__ == "__main__":
    unittest.main()
