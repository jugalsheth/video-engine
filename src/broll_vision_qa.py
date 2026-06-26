from __future__ import annotations

import base64
import json
import os
import re
from pathlib import Path

HAIKU_MODEL = "claude-haiku-4-5-20251001"
QA_COST_USD = 0.002


def vision_qa_enabled() -> bool:
    return os.getenv("AI_VISION_QA", "false").lower() in ("1", "true", "yes")


def _parse_verdict(text: str) -> tuple[bool, str]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            passed = bool(data.get("pass") or data.get("passed"))
            reason = str(data.get("reason") or data.get("issue") or "")
            return passed, reason
    except json.JSONDecodeError:
        pass
    lowered = cleaned.lower()
    if "pass" in lowered and "fail" not in lowered:
        return True, cleaned
    if "fail" in lowered:
        return False, cleaned
    return True, cleaned


def check_broll_image(
    image_path: Path,
    phrase: str,
    visual_brief: str,
) -> tuple[bool, str]:
    """Return (passed, reason). Skips (True, '') when API unavailable."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key or not image_path.exists():
        return True, ""

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        data = base64.standard_b64encode(image_path.read_bytes()).decode()
        prompt = (
            f"Does this image illustrate the spoken phrase '{phrase}'?\n"
            f"Expected visual: {visual_brief}\n"
            "Reject if: people or faces visible, legible text, generic server-room stock photo "
            "unrelated to the phrase, or obvious semantic mismatch.\n"
            'Reply JSON only: {"pass": true|false, "reason": "..."}'
        )
        response = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=200,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": data,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )
        text = response.content[0].text if response.content else ""
        return _parse_verdict(text)
    except Exception as exc:
        print(f"   Vision QA skipped: {exc}")
        return True, ""
