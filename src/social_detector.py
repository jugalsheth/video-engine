from __future__ import annotations

import json
from pathlib import Path

from src.conflict_helpers import occupied_ranges, overlaps
from src.frame_utils import normalize
from src.trigger_utils import resolve_phrase_frame
from src.pipeline_config import ai_images_enabled

SOCIAL_DURATION_FRAMES = 90
CONFLICT_SHOT_TYPES = {"TITLE_CARD", "CUSTOM_VISUAL"}
TITLE_END_BUFFER_FRAMES = 12
SOCIAL_TYPES = {"tweet", "headline", "chat", "reaction"}


def _occupied_ranges(shot_list: dict) -> list[tuple[int, int]]:
    return occupied_ranges(shot_list, moment_type="social")


def _overlaps(start: int, end: int, ranges: list[tuple[int, int]]) -> bool:
    return bool(overlaps(start, end, ranges))


def _moment_from_visual(vm: dict, start: int) -> dict | None:
    vm_type = (vm.get("type") or "").lower()
    if vm_type not in SOCIAL_TYPES:
        return None

    end = start + SOCIAL_DURATION_FRAMES
    base = {
        "type": vm_type,
        "start_frame": start,
        "end_frame": end,
        "at_phrase": vm.get("at_phrase", ""),
        "source": "visual_moments",
    }

    if vm_type == "tweet":
        base["props"] = {
            "handle": vm.get("handle") or vm.get("label") or "@creator",
            "display_name": vm.get("display_name") or vm.get("label") or "Creator",
            "text": vm.get("text") or vm.get("graphic") or "",
            "verified": bool(vm.get("verified", False)),
            "avatar_file": vm.get("avatar_file"),
        }
    elif vm_type == "headline":
        base["props"] = {
            "source": vm.get("source") or vm.get("label") or "BREAKING",
            "headline": vm.get("headline") or vm.get("graphic") or "",
            "subheadline": vm.get("subheadline") or vm.get("subtitle") or "",
        }
    elif vm_type == "chat":
        messages = vm.get("messages") or []
        if not messages and vm.get("graphic"):
            messages = [{"sender": "them", "text": vm.get("graphic", "")}]
        base["props"] = {
            "platform": vm.get("platform") or "imessage",
            "messages": messages,
        }
    elif vm_type == "reaction":
        base["props"] = {
            "emoji": vm.get("emoji") or vm.get("graphic") or "🤯",
            "label": vm.get("label") or "",
            "image_file": vm.get("image_file"),
        }
    return base


def _seed_from_config(cfg: dict, transcript: dict, occupied: list[tuple[int, int]]) -> list[dict]:
    moments: list[dict] = []
    words = transcript.get("words", [])
    full_text = transcript.get("full_text", "")

    for entry in cfg.get("social_moments") or []:
        if not isinstance(entry, dict):
            continue
        phrase = entry.get("at_phrase", "")
        if not phrase:
            continue
        start, _method = resolve_phrase_frame(words, full_text, phrase)
        if start is None:
            continue
        end = start + SOCIAL_DURATION_FRAMES
        if _overlaps(start, end, occupied):
            continue
        moment = _moment_from_visual(entry, start)
        if moment:
            moment["source"] = "project_config"
            moments.append(moment)
    return moments


def detect(
    transcript: dict,
    shot_list: dict,
    script: dict | None = None,
    project_config: dict | None = None,
) -> dict:
    words = transcript.get("words", [])
    full_text = transcript.get("full_text", "")
    norm_full = normalize(full_text)
    occupied = _occupied_ranges(shot_list)
    moments: list[dict] = []
    skipped: list[dict] = []
    seen_types: set[str] = set()

    if script is None:
        script = shot_list.get("script_metadata")

    if project_config:
        moments.extend(_seed_from_config(project_config, transcript, occupied))

    for vm in (script or {}).get("visual_moments") or []:
        if not isinstance(vm, dict):
            continue
        vm_type = (vm.get("type") or "").lower()
        if vm_type not in SOCIAL_TYPES:
            continue
        phrase = vm.get("at_phrase", "")
        if not phrase or normalize(phrase) not in norm_full:
            skipped.append({**vm, "reason": "phrase not in transcript"})
            continue
        if vm_type in seen_types and vm_type in {"tweet", "headline"}:
            continue
        start = frame_for_phrase(words, full_text, phrase)
        if start is None:
            skipped.append({**vm, "reason": "frame not found"})
            continue
        end = start + SOCIAL_DURATION_FRAMES
        if _overlaps(start, end, occupied):
            skipped.append({**vm, "reason": "conflicts with title/custom visual"})
            continue
        if any(m["start_frame"] == start for m in moments):
            continue
        moment = _moment_from_visual(vm, start)
        if moment:
            seen_types.add(vm_type)
            moments.append(moment)

    # Optional AI avatars for tweets when enabled
    if ai_images_enabled():
        from src import fal_client

        public = Path(__file__).resolve().parent.parent / "remotion" / "public"
        avatars_dir = public / "ai_images" / "avatars"
        avatars_dir.mkdir(parents=True, exist_ok=True)
        for moment in moments:
            if moment.get("type") != "tweet":
                continue
            props = moment.setdefault("props", {})
            if props.get("avatar_file"):
                continue
            handle = str(props.get("handle", "user")).lstrip("@")
            dest = avatars_dir / f"{handle}.png"
            rel = f"ai_images/avatars/{handle}.png"
            prompt = (
                f"Minimal flat avatar portrait for social media user @{handle}, "
                "abstract geometric face, dark background, no text"
            )
            path, _meta = fal_client.generate_image(prompt, dest=dest, model="flux-schnell", size="square_hd")
            if path:
                props["avatar_file"] = rel

    moments.sort(key=lambda m: m["start_frame"])
    return {
        "moments": moments,
        "skipped": skipped,
        "summary": {
            "detected": len(moments),
            "skipped": len(skipped),
            "types": [m["type"] for m in moments],
        },
    }


def save(result: dict, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2))
    return path
