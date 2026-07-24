"""Inject resolved hook_visual heroes into broll_moments for Remotion."""

from __future__ import annotations

from pathlib import Path


def inject_hero_moment(
    broll_result: dict,
    hook_visual_summary: dict,
    script: dict | None = None,
    *,
    fps: float = 30.0,
) -> dict:
    """
    Prepend an immersive_flash moment using the generated hero still.

    Mutates broll_result['moments'] in place. Returns summary of injection.
    """
    out = {"injected": False, "deferred": 0, "reason": None}
    path = hook_visual_summary.get("path")
    if not path:
        out["reason"] = "no_path"
        return out

    # Remotion staticFile paths are relative to public/
    image_file = str(path).replace("\\", "/")
    if image_file.startswith("/"):
        # absolute — try to keep ai_images/... suffix
        marker = "ai_images/"
        if marker in image_file:
            image_file = image_file[image_file.index(marker) :]
        else:
            image_file = Path(image_file).name
            image_file = f"ai_images/heroes/{image_file}"

    hook = (script or {}).get("hook_visual") if isinstance((script or {}).get("hook_visual"), dict) else {}
    try:
        duration_s = float(hook.get("duration_s") or 2.5)
    except (TypeError, ValueError):
        duration_s = 2.5
    duration_s = max(1.5, min(duration_s, 3.5))
    end_frame = max(int(round(duration_s * fps)), 45)

    moments = list(broll_result.get("moments") or [])
    deferred = 0
    shifted: list[dict] = []
    for m in moments:
        # Reuse: if already immersive in hook window, replace image instead of stacking
        if (
            m.get("layout") == "immersive_flash"
            and int(m.get("start_frame") or 0) < end_frame
            and not m.get("is_hook_hero")
        ):
            m = dict(m)
            m["image_file"] = image_file
            m["source"] = "hook_visual"
            m["is_hook_hero"] = True
            m["start_frame"] = 0
            m["end_frame"] = end_frame
            m["keyword"] = m.get("keyword") or "hook_hero"
            shifted.append(m)
            out["injected"] = True
            out["reason"] = "replaced_existing_immersive"
            # continue shifting others
            continue
        start = int(m.get("start_frame") or 0)
        end = int(m.get("end_frame") or start)
        if start < end_frame and not m.get("is_hook_hero"):
            # defer past hero
            length = max(end - start, 1)
            m = dict(m)
            m["start_frame"] = end_frame + 5
            m["end_frame"] = m["start_frame"] + length
            deferred += 1
        shifted.append(m)

    if not out["injected"]:
        hero = {
            "type": "terminal",
            "keyword": "hook_hero",
            "start_frame": 0,
            "end_frame": end_frame,
            "layout": "immersive_flash",
            "image_file": image_file,
            "source": "hook_visual",
            "is_hook_hero": True,
            "search_query": "hook visual hero",
        }
        shifted.insert(0, hero)
        out["injected"] = True
        out["reason"] = "prepended"

    # Deduplicate multiple hook heroes
    cleaned: list[dict] = []
    seen_hero = False
    for m in shifted:
        if m.get("is_hook_hero"):
            if seen_hero:
                continue
            seen_hero = True
        cleaned.append(m)

    broll_result["moments"] = cleaned
    summary = broll_result.setdefault("summary", {})
    summary["detected"] = len(cleaned)
    out["deferred"] = deferred
    return out
