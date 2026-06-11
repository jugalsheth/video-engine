from __future__ import annotations

"""
CapCut-style rhythm: visual change every 2–4 seconds.
Fills gaps with micro fun FX when detectors under-deliver.
"""

from src.frame_utils import frame_for_char_index, normalize

MAX_GAP_FRAMES = 120  # 4s at 30fps
MIN_GAP_FRAMES = 60   # 2s
RHYTHM_FUN_DURATION = 36
GAP_FILL_TYPES = ["comic_sfx", "emoji_pop", "manga_lines"]

ENERGY_FILL_WORDS = [
    "wild", "secret", "truth", "right", "unless", "finally", "wrong",
    "insane", "really", "listen", "boom", "now", "but", "wait",
]


def _event_frames(
    shot_list: dict,
    fun_result: dict,
    broll_result: dict,
) -> list[int]:
    frames: set[int] = {0}
    for shot in shot_list.get("shots", []):
        if shot.get("type") in {"TITLE_CARD", "STAT_CALLOUT", "STEP_REVEAL", "ZOOM_CLOSER"}:
            frames.add(shot["start_frame"])
    for m in fun_result.get("moments", []):
        frames.add(m["start_frame"])
    for m in broll_result.get("moments", []):
        frames.add(m["start_frame"])
    return sorted(frames)


def _find_gaps(event_frames: list[int], total_frames: int) -> list[tuple[int, int]]:
    gaps: list[tuple[int, int]] = []
    if not event_frames:
        return [(0, total_frames)]
    prev = event_frames[0]
    for f in event_frames[1:]:
        gap = f - prev
        if gap >= MAX_GAP_FRAMES:
            gaps.append((prev, f))
        prev = f
    if total_frames - prev >= MAX_GAP_FRAMES:
        gaps.append((prev, total_frames))
    return gaps


def _word_near_frame(words: list, target: int, full_text: str) -> dict | None:
    best = None
    best_dist = 999999
    norm_full = normalize(full_text)
    for w in words:
        token = normalize(w.get("word", ""))
        if token not in ENERGY_FILL_WORDS and len(token) < 5:
            continue
        dist = abs(w["start_frame"] - target)
        if dist < best_dist and dist <= 45:
            best_dist = dist
            best = w
    if best:
        return best
    for w in words:
        dist = abs(w["start_frame"] - target)
        if dist < best_dist and dist <= 30:
            best_dist = dist
            best = w
    return best


def fill_fun_gaps(
    transcript: dict,
    shot_list: dict,
    fun_result: dict,
    broll_result: dict,
    template: dict,
) -> dict:
    """Inject rhythm fun moments into gaps > 4s."""
    words = transcript.get("words", [])
    total = transcript.get("total_frames", 0)
    full_text = transcript.get("full_text", "")
    max_gap = int(template.get("visual_change_max_gap_s", 4) * transcript.get("fps", 30))

    events = _event_frames(shot_list, fun_result, broll_result)
    gaps = [(a, b) for a, b in _find_gaps(events, total) if b - a >= max_gap]

    existing = list(fun_result.get("moments", []))
    used_starts = {m["start_frame"] for m in existing}
    injected: list[dict] = []
    side_toggle = len(existing)

    for gap_start, gap_end in gaps:
        mid = gap_start + (gap_end - gap_start) // 2
        if any(abs(mid - s) < MIN_GAP_FRAMES for s in used_starts):
            continue
        word_obj = _word_near_frame(words, mid, full_text)
        if not word_obj:
            continue
        start = word_obj["start_frame"]
        if start in used_starts:
            continue
        fun_type = GAP_FILL_TYPES[len(injected) % len(GAP_FILL_TYPES)]
        keyword = word_obj.get("word", "BOOM")
        side = "left" if side_toggle % 2 == 0 else "right"
        side_toggle += 1
        moment = {
            "type": fun_type,
            "start_frame": start,
            "end_frame": start + RHYTHM_FUN_DURATION,
            "keyword": keyword,
            "mood": fun_result.get("mood", "chaos"),
            "side": side,
            "source": "rhythm_fill",
        }
        if fun_type == "comic_sfx":
            moment["text"] = keyword.upper()[:8] + "!"
        elif fun_type == "emoji_pop":
            moment["emoji"] = "🔥" if side_toggle % 2 else "⚡"
        injected.append(moment)
        used_starts.add(start)

    min_events = template.get("min_visual_events", 12)
    all_moments = existing + injected
    total_events = len(_event_frames(shot_list, {"moments": all_moments}, broll_result))

    result = {**fun_result, "moments": existing + injected}
    result["summary"] = {
        **fun_result.get("summary", {}),
        "rhythm_injected": len(injected),
        "total_visual_events": total_events,
        "min_target": min_events,
    }
    if injected:
        print(f"   Rhythm fill: +{len(injected)} fun FX in {len(gaps)} gap(s)")
    return result


def _apply_dynamic_step_holds(shots: list, total_frames: int) -> None:
    """Hold each STEP_REVEAL until the next step, payoff, or closer."""
    step_shots = sorted(
        [s for s in shots if s.get("type") == "STEP_REVEAL"],
        key=lambda s: s["start_frame"],
    )
    if not step_shots:
        return

    closer = next((s for s in shots if s.get("type") == "ZOOM_CLOSER"), None)
    fallback_end = (closer["start_frame"] - 30) if closer else max(
        step_shots[-1]["start_frame"] + 90, total_frames - 30
    )

    for i, shot in enumerate(step_shots):
        if i + 1 < len(step_shots):
            next_start = step_shots[i + 1]["start_frame"]
            shot["end_frame"] = max(next_start, shot["start_frame"] + 30)
        else:
            shot["end_frame"] = max(fallback_end, shot["start_frame"] + 90)


def apply_template_to_shots(shot_list: dict, template: dict) -> dict:
    """Tune hold durations from template."""
    title_frames = template.get("title_card_frames")
    stat_hold = template.get("stat_hold_frames")
    if not any([title_frames, stat_hold]):
        if not template.get("id"):
            return shot_list

    shots = shot_list.get("shots", [])
    total_frames = shot_list.get("total_frames", 0)

    for shot in shots:
        t = shot.get("type")
        if t == "TITLE_CARD" and title_frames:
            shot["end_frame"] = shot["start_frame"] + title_frames
        elif t == "STAT_CALLOUT" and stat_hold:
            shot["end_frame"] = shot["start_frame"] + stat_hold

    _apply_dynamic_step_holds(shots, total_frames)

    shot_list["edit_template"] = template.get("id", "THREE_STEP_HOT_TAKE")
    shot_list["template_slots"] = template.get("slots", [])
    return shot_list
