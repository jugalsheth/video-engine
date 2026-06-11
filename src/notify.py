from __future__ import annotations

"""
Sends finished video to Telegram with caption and hashtags.
"""

import os
from pathlib import Path

import httpx


def _escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def send(
    shot_list: dict,
    script: dict | None,
    output_path: str,
    render_mins: float,
) -> None:
    """Upload video to Telegram with posting-ready caption."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("   Telegram credentials missing — skipping notification")
        return

    caption = shot_list.get("caption_for_posting", "")
    hashtags = shot_list.get("hashtags", [])
    hashtag_str = " ".join(hashtags) if hashtags else ""

    title = shot_list.get("video_title", "Video")
    territory = shot_list.get("territory", "")
    script_note = ""
    if script:
        script_note = f"\n📜 Matched script #{script.get('script_number', '?')}"

    message = (
        f"🎬 <b>{_escape_html(title)}</b>\n"
        f"🏷 {_escape_html(territory)}\n"
        f"⏱ Rendered in {render_mins:.1f} min{script_note}\n\n"
        f"{_escape_html(caption)}\n\n"
        f"{_escape_html(hashtag_str)}"
    )

    url = f"https://api.telegram.org/bot{token}/sendVideo"
    output_path = Path(output_path)

    try:
        with output_path.open("rb") as video_file:
            response = httpx.post(
                url,
                data={"chat_id": chat_id, "caption": message, "parse_mode": "HTML"},
                files={"video": (output_path.name, video_file, "video/mp4")},
                timeout=120,
            )
        response.raise_for_status()
        print("   Telegram notification sent")
    except Exception as e:
        print(f"   Telegram send failed: {e}")
