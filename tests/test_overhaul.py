from __future__ import annotations

import pytest

from src.trigger_utils import resolve_phrase_frame


def _words(text: str) -> list[dict]:
    parts = text.split()
    return [
        {
            "word": w,
            "start": i * 0.3,
            "end": (i + 1) * 0.3,
            "start_frame": i * 9,
            "end_frame": (i + 1) * 9,
        }
        for i, w in enumerate(parts)
    ]


def test_resolve_phrase_fuzzy_match():
    words = _words("open ai is wild today")
    full_text = "open ai is wild today"
    frame, method = resolve_phrase_frame(words, full_text, "openai")
    assert frame is not None
    assert method in {"fuzzy", "collapsed", "flex", "exact"}


def test_logo_openai_collapsed_index():
    words = _words("we use open ai for coding")
    full_text = "we use open ai for coding"
    frame, method = resolve_phrase_frame(words, full_text, "open ai")
    assert frame == words[2]["start_frame"]
    assert method in {"exact", "flex", "collapsed"}


def test_broll_pairing_skips_composited():
    from src.broll_detector import _pair_broll_to_steps

    shot_list = {
        "shots": [
            {
                "type": "STEP_REVEAL",
                "start_frame": 300,
                "end_frame": 360,
                "params": {"step_number": 1},
            }
        ]
    }
    moments = [
        {
            "start_frame": 280,
            "end_frame": 385,
            "layout": "presenter_on_bg",
            "keyword": "test",
        },
        {
            "start_frame": 310,
            "end_frame": 415,
            "layout": "pip",
            "keyword": "other",
        },
    ]
    result = _pair_broll_to_steps(moments, shot_list, None)
    composited = next(m for m in result if m["layout"] == "presenter_on_bg")
    assert composited["start_frame"] == 280
    pip = next(m for m in result if m.get("layout") == "pip")
    assert pip.get("step_paired") == 1


def test_trigger_audit_covers_broll_phrases():
    from src.trigger_audit import audit

    words = _words("overspent on cursor tokens")
    transcript = {"words": words, "full_text": "overspent on cursor tokens"}
    script = {
        "video_triggers": {
            "broll_phrases": ["overspent on cursor"],
            "broll_layouts": ["presenter_on_bg"],
            "broll_image_descriptions": ["Dark IDE workspace with code editor, no people"],
        }
    }
    result = audit(transcript, script)
    assert result["passed"]
    assert result["matched"] >= 1


def test_build_broll_prompt_unique_per_phrase():
    from src.ai_image_gen import build_broll_prompt

    script = {
        "title_overlay": "STOP OVERPAYING FOR AI",
        "territory": "AI Demystified",
        "video_triggers": {
            "broll_phrases": ["free model", "premium model"],
            "broll_image_descriptions": [
                "Pricing tier UI with FREE badge",
                "Architecture blueprint for reasoning",
            ],
        },
    }
    m1 = {
        "keyword": "free model",
        "layout": "presenter_on_bg",
        "transcript_context": "use a free model for tasks",
    }
    m2 = {
        "keyword": "premium model",
        "layout": "presenter_on_bg",
        "transcript_context": "reserve premium model for reasoning",
    }
    p1 = build_broll_prompt(m1, script)
    p2 = build_broll_prompt(m2, script)
    assert p1 != p2
    assert "Pricing tier" in p1
    assert "Architecture blueprint" in p2
    assert "free model" in p1.lower()


def test_template_for_free_model():
    from src.broll_visual_context import template_for_phrase

    assert template_for_phrase("free model") is not None
    assert "pricing" in template_for_phrase("free model").lower()


def test_trigger_audit_broll_description_length():
    from src.trigger_audit import audit

    transcript = {"words": [], "full_text": ""}
    script = {
        "video_triggers": {
            "broll_phrases": ["free model", "premium model"],
            "broll_image_descriptions": ["only one"],
        }
    }
    result = audit(transcript, script, strict=True)
    assert not result["passed"]
    assert result["validation_errors"]

    from src.cut_and_remap import _build_frame_map, _remap_frame

    kept = [{"start_s": 0.0, "end_s": 3.0}, {"start_s": 4.0, "end_s": 7.0}]
    frame_map, _total = _build_frame_map(kept, fps=30)
    assert _remap_frame(30, frame_map) <= _remap_frame(60, frame_map)
    assert _remap_frame(150, frame_map) > _remap_frame(60, frame_map)
