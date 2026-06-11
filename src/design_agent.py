from __future__ import annotations

"""
The intelligence core.
Claude Sonnet reads the transcript + design rules + script metadata
and produces a frame-accurate animation shot list.
"""

import json
import os
from pathlib import Path

import anthropic

ENGINE_ROOT = Path(__file__).resolve().parent.parent
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def load_rules() -> dict:
    rules_dir = ENGINE_ROOT / "rules"
    return {
        "design": (rules_dir / "design_rules.txt").read_text(),
        "animations": (rules_dir / "animation_library.txt").read_text(),
        "assets": (rules_dir / "asset_map.txt").read_text(),
    }


def fallback_shot_list(transcript: dict, script: dict | None) -> dict:
    """Minimal shot list — captions only, no design agent animations."""
    title = "UNTITLED"
    caption = transcript.get("full_text", "")[:120]
    hashtags = ["#CareerTips", "#TechCareers", "#AIEngineer", "#LinkedIn", "#Reels"]

    if script:
        title = script.get("title_overlay", title)
        caption = script.get("caption_hook", caption)
        hashtags = script.get("hashtags", hashtags)

    return {
        "video_title": title,
        "territory": script.get("territory", "general") if script else "general",
        "total_frames": transcript["total_frames"],
        "fps": transcript["fps"],
        "caption_for_posting": caption,
        "hashtags": hashtags,
        "shots": [
            {
                "type": "ZOOM_HOOK",
                "start_frame": 0,
                "end_frame": 32,
                "params": {
                    "snap_frames": 6,
                    "hold_frames": 6,
                    "ease_frames": 20,
                    "peak_scale": 1.18,
                    "settle_scale": 1.06,
                },
            },
            {
                "type": "TITLE_CARD",
                "start_frame": 0,
                "end_frame": 45,
                "params": {
                    "text": title,
                    "subtitle": "",
                    "animation": "slam_up",
                },
            },
            {
                "type": "CAPTION_HIGHLIGHT",
                "start_frame": 0,
                "end_frame": transcript["total_frames"],
                "params": {"auto": True},
            },
        ],
    }


def generate(transcript: dict, script: dict | None) -> dict:
    """
    Generates complete animation shot list from transcript.
    Script metadata enriches the output if available.
    Works in transcript-only mode if no script matched.
    """
    rules = load_rules()

    script_context = (
        json.dumps(script, indent=2)
        if script
        else "No script matched. Use transcript structure to infer meaning."
    )

    prompt = f"""You are an expert video editor and motion graphics designer
specializing in short-form educational content for Instagram Reels 
and LinkedIn Video. You create animation shot lists that make viewers 
stay, engage, and save.

DESIGN RULES (follow exactly):
{rules['design']}

AVAILABLE ANIMATIONS:
{rules['animations']}

STOCK B-ROLL TYPES (auto-detected by pipeline — do NOT use PNG asset_map):
salary, linkedin, checklist, data_flow, terminal, neural_network, growth_chart
B-roll is fetched from Pexels/Pixabay at render time. Max 1 cut per 8 seconds.

LEGACY ASSET MAP (reference only):
{rules['assets']}

TRANSCRIPT WITH FRAME-ACCURATE TIMESTAMPS:
{json.dumps(transcript['words'], indent=2)}

VIDEO DURATION: {transcript['duration_seconds']}s | {transcript['total_frames']} frames | {transcript['fps']}fps

SCRIPT METADATA:
{script_context}

YOUR TASK:
Analyze the transcript word by word. Identify the structure:
- First spoken line = the hook
- Any percentage, number, or stat = STAT_CALLOUT moment  
- "One/Two/Three" or "First/Second/Third" or "Step" = STEP_REVEAL
- Last 3 seconds = the closer
- Energy words (Right, Unless, Listen, That's all) = WORD_HIGHLIGHT
- Do NOT add BROLL_OVERLAY shots — stock B-roll is auto-detected by the pipeline
- If script metadata provided, use title_overlay for TITLE_CARD text
  and use hook_type to inform the opening animation energy level

Design an animation layout for THIS specific video.
Not a template. The animations should serve what is actually being said.

Rules:
- Captions use VIRAL mode: max 2 words on screen, all-caps, amber active word
- Always start with ZOOM_HOOK (32 frames: snap 6, hold 6, ease 20 — peak 1.18, settle 1.06)
- Always pair TITLE_CARD at frame 0 with animation "slam_up", minimum 120 frames duration
- Subtle is the enemy — every animation must be bold and scroll-stopping
- Always include CAPTION_HIGHLIGHT for full duration
- Never put more than 2 elements on screen simultaneously
- Never cover the creator's face
- Step reveals are always sequential, never simultaneous
- Stat callouts trigger on the EXACT frame the number is spoken

Return ONLY valid JSON. No markdown. No backticks. No explanation:
{{
  "video_title": "derived from transcript or script title_overlay",
  "territory": "from script or inferred from transcript",
  "total_frames": {transcript['total_frames']},
  "fps": {transcript['fps']},
  "caption_for_posting": "one compelling sentence for IG/LinkedIn",
  "hashtags": ["#Tag1", "#Tag2", "#Tag3", "#Tag4", "#Tag5"],
  "shots": [
    {{
      "type": "ZOOM_HOOK",
      "start_frame": 0,
      "end_frame": 32,
      "params": {{
        "snap_frames": 6,
        "hold_frames": 6,
        "ease_frames": 20,
        "peak_scale": 1.18,
        "settle_scale": 1.06
      }}
    }},
    {{
      "type": "TITLE_CARD",
      "start_frame": 0,
      "end_frame": 120,
      "params": {{
        "text": "TITLE IN CAPS",
        "subtitle": "short subtitle",
        "animation": "slam_up"
      }}
    }},
    {{
      "type": "CAPTION_HIGHLIGHT",
      "start_frame": 0,
      "end_frame": {transcript['total_frames']},
      "params": {{"auto": true}}
    }}
  ]
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    shot_list = json.loads(raw)
    print(f"   Shot list: {len(shot_list['shots'])} shots planned")
    print(f"   Title: {shot_list.get('video_title', 'untitled')}")
    return shot_list
