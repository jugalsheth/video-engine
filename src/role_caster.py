from __future__ import annotations

import json
import re
from pathlib import Path

from src.conflict_helpers import occupied_ranges, overlaps
from src.frame_utils import normalize
from src.trigger_utils import resolve_phrase_frame
from src.fun_detector import detect_mood
from src.rules_loader import load_role_keywords

ROLE_DURATION_FRAMES = 75
RATE_LIMIT_MEDIUM = 240
RATE_LIMIT_CHAOS = 150

ROLE_RULES: dict[str, dict] = {
    "victim": {
        "keywords": [
            "broke at 3am", "3am", "broke", "failure", "fail", "inevitable",
            "wrong", "error", "pain", "window", "messy",
        ],
        "poses": {
            "default": "melting",
            "callback": "coffee",
        },
        "lines": {
            "3am": "3 AM AGAIN?!",
            "broke": "IT BROKE?!",
            "fail": "NOT AGAIN...",
            "failure": "WHY ME",
            "inevitable": "CALLED IT",
            "default": "OUCH",
        },
        "min_mood": 0,
    },
    "hype": {
        "keywords": [
            "finally", "works", "saved", "success", "landed", "nailed",
            "hours saved", "hours every week", "win",
        ],
        "poses": {"default": "celebrate", "callback": "thumbs_up"},
        "lines": {
            "saved": "LET'S GO!",
            "success": "W WE WIN",
            "works": "IT WORKS!",
            "hours": "HUGE W",
            "default": "YESSS",
        },
        "min_mood": 0,
    },
    "skeptic": {
        "keywords": [
            "at least", "really", "unless", "but", "wonder", "normal", "sure",
        ],
        "poses": {"default": "eyebrow", "callback": "arms_crossed"},
        "lines": {
            "at least": "SURE... OKAY",
            "really": "REALLY THO?",
            "unless": "UNLESS...?",
            "normal": "THAT'S NORMAL?",
            "default": "HMM",
        },
        "min_mood": 0,
    },
    "expert": {
        "keywords": [
            "data pipeline", "production data", "python script", "python",
            "transform", "engineering", "warehouse", "metrics",
        ],
        "poses": {"default": "point", "callback": "explain"},
        "lines": {
            "pipeline": "CLASSIC PIPELINE",
            "python": "PYTHON TIME",
            "data": "DATA LIFE",
            "system": "PRODUCTION SYS",
            "default": "TECHNICALLY...",
        },
        "min_mood": 0,
    },
    "gremlin": {
        "keywords": ["insane", "wild", "crazy", "literally", "chaos", "boom"],
        "poses": {"default": "chaos", "callback": "troll"},
        "lines": {
            "insane": "CHAOS MODE",
            "wild": "FERAL",
            "crazy": "UNHINGED",
            "default": "LET'S GOOO",
        },
        "min_mood": 1,
    },
}

CONFLICT_SHOT_TYPES = {"TITLE_CARD", "CUSTOM_VISUAL"}
TITLE_END_BUFFER_FRAMES = 12


def _merge_role_keywords() -> dict[str, dict]:
    merged = {k: {**v, "keywords": list(v["keywords"])} for k, v in ROLE_RULES.items()}
    file_kw = load_role_keywords()
    for role, keywords in file_kw.items():
        if role in merged:
            existing = set(merged[role]["keywords"])
            for kw in keywords:
                if kw not in existing:
                    merged[role]["keywords"].append(kw)
        else:
            merged[role] = {
                "keywords": keywords,
                "poses": {"default": "point"},
                "lines": {"default": "OK"},
                "min_mood": 0,
            }
    return merged


def _occupied_ranges(shot_list: dict) -> list[tuple[int, int]]:
    return occupied_ranges(shot_list, moment_type="role")


def _overlaps(start: int, end: int, ranges: list[tuple[int, int]]) -> bool:
    return bool(overlaps(start, end, ranges))


def _pick_line(role: str, keyword: str, role_rules: dict | None = None) -> str:
    rules = (role_rules or _merge_role_keywords())[role]["lines"]
    k = keyword.lower()
    for key, line in rules.items():
        if key != "default" and key in k:
            return line
    return rules.get("default", keyword.upper()[:18])


def _pick_pose(role: str, is_callback: bool, role_rules: dict | None = None) -> str:
    poses = (role_rules or _merge_role_keywords())[role]["poses"]
    return poses.get("callback", poses["default"]) if is_callback else poses["default"]


def detect(transcript: dict, shot_list: dict) -> dict:
    words = transcript.get("words", [])
    occupied = _occupied_ranges(shot_list)
    mood = detect_mood(transcript)
    mood_tier = 1 if mood == "chaos" else 0
    rate_limit = RATE_LIMIT_CHAOS if mood == "chaos" else RATE_LIMIT_MEDIUM

    role_rules = _merge_role_keywords()
    full_text = normalize(transcript.get("full_text", ""))
    moments: list[dict] = []
    skipped: list[dict] = []
    role_last_frame: dict[str, int] = {}
    side_toggle = 0

    all_phrases: list[tuple[str, str]] = []
    for role, cfg in role_rules.items():
        if cfg["min_mood"] > mood_tier:
            continue
        for kw in sorted(cfg["keywords"], key=len, reverse=True):
            all_phrases.append((role, kw))
    all_phrases.sort(key=lambda x: len(x[1]), reverse=True)

    used_spans: list[tuple[int, int]] = []
    seen_roles: set[str] = set()

    for role, phrase in all_phrases:
        if role in seen_roles:
            continue
        start, match_method = resolve_phrase_frame(words, transcript.get("full_text", ""), phrase)
        if start is None:
            skipped.append({"role": role, "keyword": phrase, "reason": "phrase not found"})
            continue
        end = start + ROLE_DURATION_FRAMES
        if _overlaps(start, end, occupied):
            skipped.append({"role": role, "start_frame": start, "keyword": phrase, "reason": "title conflict"})
            continue

        is_callback = role in role_last_frame and start - role_last_frame[role] > 300
        side = "left" if side_toggle % 2 == 0 else "right"
        side_toggle += 1

        moment = {
            "role": role,
            "pose": _pick_pose(role, is_callback, role_rules),
            "line": _pick_line(role, phrase, role_rules),
            "start_frame": start,
            "end_frame": end,
            "keyword": phrase,
            "mood": mood,
            "side": side,
            "is_callback": is_callback,
        }
        moments.append(moment)
        seen_roles.add(role)
        role_last_frame[role] = start
        used_spans.append((start, start + ROLE_DURATION_FRAMES))

    # Number wins → hype role if not matched
    if "hype" not in seen_roles:
        for word_obj in words:
            token = word_obj.get("word", "").strip()
            if not re.match(r"^\d+$", token.replace(",", "")):
                continue
            val = int(re.sub(r"\D", "", token) or "0")
            if val < 2:
                continue
            start = word_obj["start_frame"]
            end = start + ROLE_DURATION_FRAMES
            if _overlaps(start, end, occupied):
                continue
            moments.append({
                "role": "hype",
                "pose": "celebrate",
                "line": f"{token}?!",
                "start_frame": start,
                "end_frame": end,
                "keyword": token,
                "mood": mood,
                "side": "right",
                "is_callback": False,
            })
            break

    moments.sort(key=lambda m: m["start_frame"])

    accepted: list[dict] = []
    last_start = -rate_limit
    for m in moments:
        if m["start_frame"] < last_start + rate_limit:
            skipped.append({**m, "reason": f"rate limit ({mood})"})
            continue
        accepted.append(m)
        last_start = m["start_frame"]

    return {
        "mood": mood,
        "moments": accepted,
        "skipped": skipped,
        "summary": {
            "detected": len(accepted),
            "skipped": len(skipped),
            "mood": mood,
            "roles": [m["role"] for m in accepted],
        },
    }


def save(result: dict, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2))
    return path
