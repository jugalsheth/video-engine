from __future__ import annotations

REQUIRED_SHOT_TYPES = {"ZOOM_HOOK", "TITLE_CARD", "CAPTION_HIGHLIGHT"}
STEP_LABEL_MAX_LEN = 28
TEMPLATE_DRIFT_SECONDS = 5


def validate(shot_list: dict, total_frames: int) -> list[str]:
    errors: list[str] = []
    warnings: list[str] = []
    shots = shot_list.get("shots", [])

    if not shot_list.get("video_title"):
        errors.append("missing video_title")

    types = {s.get("type") for s in shots}
    for req in REQUIRED_SHOT_TYPES:
        if req not in types:
            errors.append(f"missing required shot type: {req}")

    for i, shot in enumerate(shots):
        st = shot.get("start_frame", -1)
        en = shot.get("end_frame", -1)
        if st < 0 or en <= st:
            errors.append(f"shot[{i}] {shot.get('type')}: invalid frame range {st}-{en}")
        if en > total_frames + 30:
            errors.append(f"shot[{i}] {shot.get('type')}: end_frame {en} exceeds video {total_frames}")

    step_shots = sorted(
        [s for s in shots if s.get("type") == "STEP_REVEAL"],
        key=lambda s: s["start_frame"],
    )
    meta = shot_list.get("script_metadata") or {}
    template_id = shot_list.get("edit_template") or meta.get("edit_template") or ""

    if template_id == "THREE_STEP_HOT_TAKE":
        visual_steps = [
            m for m in (meta.get("visual_moments") or [])
            if isinstance(m, dict) and m.get("type") == "step"
        ]
        if len(visual_steps) < 3:
            warnings.append(
                f"THREE_STEP_HOT_TAKE expects 3 visual_moments steps; found {len(visual_steps)}"
            )
        if len(step_shots) < 3:
            warnings.append(
                f"only {len(step_shots)} STEP_REVEAL shots detected (expected 3)"
            )

    for shot in step_shots:
        label = str(shot.get("params", {}).get("text", ""))
        if len(label) > STEP_LABEL_MAX_LEN:
            warnings.append(
                f"step {shot.get('params', {}).get('step_number')} label truncated risk: "
                f"'{label[:40]}...' ({len(label)} chars)"
            )

    fps = shot_list.get("fps", 30)
    slots = shot_list.get("template_slots") or []
    step_slots = [s for s in slots if s.get("name", "").startswith("step_")]
    for i, shot in enumerate(step_shots):
        if i >= len(step_slots):
            break
        slot = step_slots[i]
        actual_s = shot["start_frame"] / fps
        slot_start = slot.get("start_s", 0)
        slot_end = slot.get("end_s", 999)
        if actual_s < slot_start - TEMPLATE_DRIFT_SECONDS or actual_s > slot_end + TEMPLATE_DRIFT_SECONDS:
            warnings.append(
                f"step {shot.get('params', {}).get('step_number')} at {actual_s:.1f}s "
                f"outside template slot {slot.get('name')} ({slot_start}-{slot_end}s)"
            )

    return errors + [f"warning: {w}" for w in warnings]
