from __future__ import annotations

from src.conflict_rules import blocking_types, title_buffer_frames


def occupied_ranges(
    shot_list: dict,
    *,
    moment_type: str = "broll",
    with_labels: bool = False,
) -> list[tuple]:
    """Build blocking ranges from shot list using shared conflict rules."""
    block = blocking_types(moment_type)
    buffer = title_buffer_frames()
    ranges: list[tuple] = []
    for shot in shot_list.get("shots", []):
        shot_type = shot.get("type")
        if shot_type not in block:
            continue
        end = shot["end_frame"]
        if shot_type == "TITLE_CARD":
            end += buffer
        if with_labels:
            ranges.append((shot["start_frame"], end, shot_type))
        else:
            ranges.append((shot["start_frame"], end))
    return ranges


def overlaps(
    start: int,
    end: int,
    ranges: list[tuple],
    *,
    ignore_labels: set[str] | None = None,
    with_labels: bool = False,
) -> str | bool | None:
    for item in ranges:
        if with_labels:
            rs, re_, label = item  # type: ignore[misc]
            if ignore_labels and label in ignore_labels:
                continue
            if start < re_ and end > rs:
                return label
        else:
            rs, re_ = item  # type: ignore[misc]
            if start < re_ and end > rs:
                return True
    return None if with_labels else False


def get_step_windows(
    shot_list: dict,
    step_beats: list | None = None,
    *,
    buffer: int | None = None,
) -> list[dict]:
    from src.conflict_rules import load_rules, step_window_buffer_frames

    buf = buffer if buffer is not None else step_window_buffer_frames()
    fallback_dur = int(load_rules().get("step_beat_fallback_duration_frames", 75))

    step_shots = [
        s for s in shot_list.get("shots", []) if s.get("type") == "STEP_REVEAL"
    ]
    if step_shots:
        return [
            {
                "start": s["start_frame"] - buf,
                "end": s["end_frame"] + buf,
                "step": s.get("params", {}).get("step_number", 0),
            }
            for s in step_shots
        ]

    if not step_beats:
        return []
    return [
        {
            "start": b["frame"] - buf,
            "end": b["frame"] + buf + fallback_dur,
            "step": b.get("step", 0),
        }
        for b in step_beats
    ]


def overlaps_step_window(
    start: int,
    end: int,
    step_windows: list[dict],
) -> bool:
    return any(
        start < w["end"] and end > w["start"] for w in step_windows
    )
