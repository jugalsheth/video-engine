"""Hero inject into broll_moments."""

from __future__ import annotations

from src.hero_inject import inject_hero_moment


def test_inject_prepends_immersive_hero():
    broll = {
        "moments": [
            {
                "keyword": "later",
                "start_frame": 10,
                "end_frame": 40,
                "layout": "pip",
            }
        ],
        "summary": {"detected": 1},
    }
    summary = inject_hero_moment(
        broll,
        {"path": "ai_images/heroes/hook_hero.png"},
        {"hook_visual": {"duration_s": 2.0}},
        fps=30,
    )
    assert summary["injected"]
    assert broll["moments"][0]["is_hook_hero"]
    assert broll["moments"][0]["layout"] == "immersive_flash"
    assert broll["moments"][0]["image_file"] == "ai_images/heroes/hook_hero.png"
    assert broll["moments"][0]["start_frame"] == 0
    assert broll["moments"][1]["start_frame"] >= broll["moments"][0]["end_frame"]


def test_inject_replaces_existing_hook_immersive():
    broll = {
        "moments": [
            {
                "keyword": "old",
                "start_frame": 0,
                "end_frame": 15,
                "layout": "immersive_flash",
                "image_file": "ai_images/moment_1.png",
            }
        ],
        "summary": {},
    }
    summary = inject_hero_moment(
        broll,
        {"path": "ai_images/heroes/hook_hero.png"},
        {"hook_visual": {"duration_s": 2.5}},
        fps=30,
    )
    assert summary["injected"]
    assert len([m for m in broll["moments"] if m.get("is_hook_hero")]) == 1
    assert broll["moments"][0]["image_file"] == "ai_images/heroes/hook_hero.png"
