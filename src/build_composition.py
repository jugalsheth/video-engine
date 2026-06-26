from __future__ import annotations

"""
Stages per-video assets into remotion/public/ for Remotion to consume.
"""

import json
import shutil
from pathlib import Path

from src import beat_detector, broll_detector, composite_assets, fetch_broll, fetch_music, fun_detector, global_fx_detector, logo_detector, lottie_assets, role_caster, social_detector, step_beat_detector
from src import ai_image_gen
from src.ai_cost_budget import AICostBudget
from src.render_props import resolve_render_props
from src.template_loader import resolve_template
from src.trigger_audit import preferred_pause_seconds
from src.visual_prompt_agent import fill_missing_descriptions, write_prompt_manifest
from src.visual_scheduler import apply_template_to_shots, fill_fun_gaps, enforce_min_visual_events
from src.caption_converter import save_srt
from src.cut_and_remap import apply_jump_cuts
from src.detect_silence import detect as detect_silence
from src.media_process import finalize_source_video
from src.pipeline_config import ai_cost_ceiling_usd, jump_cuts_enabled, resolve_config
from src.staging import (
    checkpoint_shot_list,
    resolve_output_dir,
    sync_staging_to_public,
    write_input_props,
)
from src.project_manager import load_project_config
from src import voice_enhance

ENGINE_ROOT = Path(__file__).resolve().parent.parent
PUBLIC_DIR = ENGINE_ROOT / "remotion" / "public"
BRAND_CONFIG_PATH = ENGINE_ROOT / "rules" / "brand_config.json"


def _load_brand_config() -> dict:
    if not BRAND_CONFIG_PATH.exists():
        return {}
    return json.loads(BRAND_CONFIG_PATH.read_text(encoding="utf-8"))


def _sync_custom_visual_shots(shot_list: dict, script: dict | None) -> None:
    if not script:
        return
    overrides = {
        o.get("trigger_phrase"): o
        for o in (script.get("custom_visual_overrides") or [])
        if o.get("trigger_phrase")
    }
    for shot in shot_list.get("shots", []):
        if shot.get("type") != "CUSTOM_VISUAL":
            continue
        trigger = shot.get("params", {}).get("trigger_phrase")
        override = overrides.get(trigger)
        if not override:
            continue
        shot["params"]["asset_status"] = override.get("asset_status", "needs_creation")
        shot["params"]["asset_filename"] = override.get("asset_filename", "")


def _stage_custom_assets(
    script: dict | None,
    shot_list: dict,
    project_assets_dir: Path | None = None,
) -> None:
    """Copy ready custom assets into remotion/public for Remotion."""
    if not script:
        return

    from src.asset_matcher import stage_assets_for_remotion

    script_id = Path(script.get("filename_hint", "script")).stem
    dest_dir = PUBLIC_DIR / "custom_assets" / script_id

    if project_assets_dir and project_assets_dir.exists():
        copied = stage_assets_for_remotion(script, project_assets_dir, dest_dir)
        if copied:
            print(f"   Staged {copied} custom asset(s) for {script_id}")
        return

    legacy_dir = ENGINE_ROOT / "raw_videos" / "custom_assets" / script_id
    if not legacy_dir.exists():
        return

    dest_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    for f in legacy_dir.iterdir():
        if f.is_file() and f.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".mp4"}:
            shutil.copy2(f, dest_dir / f.name)
            copied += 1
    if copied:
        print(f"   Staged {copied} custom asset(s) for {script_id} (legacy path)")


def prepare(
    video_path: str,
    transcript: dict,
    shot_list: dict,
    script: dict | None = None,
    project_assets_dir: Path | None = None,
    *,
    regenerate_ai: bool = False,
) -> dict:
    video_path = Path(video_path).resolve()
    OUT_DIR, project_id = resolve_output_dir(project_assets_dir)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if project_id:
        resolve_config(project_id)

    dest_video = OUT_DIR / "source.mp4"
    dest_cut = OUT_DIR / "source_cut.mp4"

    template = resolve_template(script)
    enriched_shot_list = apply_template_to_shots({**shot_list}, template)
    brand_config = _load_brand_config()
    if script:
        enriched_shot_list["script_metadata"] = {
            "title_overlay": script.get("title_overlay"),
            "subtitle_overlay": script.get("subtitle_overlay"),
            "open_loop_plant": script.get("open_loop_plant"),
            "open_loop_payoff": script.get("open_loop_payoff"),
            "hook_type": script.get("hook_type"),
            "script_number": script.get("script_number"),
            "edit_template": script.get("edit_template") or template.get("id"),
            "count_promise": script.get("count_promise"),
            "recording_cues": script.get("recording_cues", []),
            "visual_moments": script.get("visual_moments", []),
            "video_triggers": script.get("video_triggers", {}),
            "delivery_notes": script.get("delivery_notes"),
            "brand": brand_config,
        }

    ai_budget = AICostBudget()
    if script:
        script, _agent_summary = fill_missing_descriptions(
            script, transcript, budget=ai_budget,
        )
        if script and enriched_shot_list.get("script_metadata"):
            enriched_shot_list["script_metadata"]["video_triggers"] = script.get(
                "video_triggers", {},
            )

    broll_result = broll_detector.detect(transcript, enriched_shot_list, script)
    fun_result = fun_detector.detect(transcript, enriched_shot_list, script)
    logo_result = logo_detector.detect(transcript, enriched_shot_list, script)
    role_result = role_caster.detect(transcript, enriched_shot_list)
    fun_result = fill_fun_gaps(
        transcript,
        enriched_shot_list,
        fun_result,
        broll_result,
        template,
        logo_result=logo_result,
        role_result=role_result,
    )
    fun_result = enforce_min_visual_events(
        transcript, enriched_shot_list, fun_result, broll_result, template,
    )
    beats_result = beat_detector.detect(transcript, script)

    render_props = resolve_render_props(script, brand_config)
    global_fx_result = global_fx_detector.detect(
        transcript, enriched_shot_list, beats_result, script, render_props,
    )

    used_cut = False
    if jump_cuts_enabled():
        try:
            pause_hints = preferred_pause_seconds(script)
            silence_map = detect_silence(video_path, preferred_pause_seconds=pause_hints or None)
            (OUT_DIR / "silence_map.json").write_text(json.dumps(silence_map, indent=2))
            if silence_map.get("removed_total_s", 0) >= 0.1:
                transcript, enriched_shot_list, broll_result, fun_result, logo_result, role_result, beats_result, global_fx_result, _ = (
                    apply_jump_cuts(
                        video_path,
                        dest_cut,
                        silence_map,
                        OUT_DIR,
                        transcript,
                        enriched_shot_list,
                        broll_result,
                        fun_result,
                        logo_result,
                        role_result,
                        beats_result,
                        global_fx_result,
                    )
                )
                used_cut = dest_cut.exists()
        except Exception as e:
            print(f"   Jump cuts skipped: {e}")

    grade_applied = False
    voice_applied = False
    try:
        if used_cut:
            tmp = dest_video.with_suffix(".final.tmp.mp4")
            finalize_source_video(dest_cut, tmp, apply_grade=False)
            shutil.move(str(tmp), str(dest_video))
            voice_applied = voice_enhance.enabled()
            if dest_cut.exists():
                dest_cut.unlink(missing_ok=True)
        else:
            src = Path(video_path)
            out = dest_video
            tmp = dest_video.with_suffix(".final.tmp.mp4") if src.resolve() == out.resolve() else out
            finalize_source_video(src, tmp, apply_grade=True)
            if tmp != out:
                shutil.move(str(tmp), str(out))
            grade_applied = True
            voice_applied = voice_enhance.enabled()
    except Exception as e:
        print(f"   Source process failed, copying raw: {e}")
        if used_cut and dest_cut.exists():
            shutil.copy2(dest_cut, dest_video)
        elif Path(video_path).resolve() != dest_video.resolve():
            shutil.copy2(video_path, dest_video)

    if grade_applied:
        print("   Color grade applied (ffmpeg)")
    if voice_applied:
        print("   Voice enhance applied (ffmpeg)")

    music_config = fetch_music.ensure_background_music(script, template)
    meta = enriched_shot_list.setdefault("script_metadata", {})
    meta["music"] = music_config
    print(f"   Music bed: {music_config.get('file')} ({music_config.get('key', 'default')})")

    stock_summary = fetch_broll.fetch_all(broll_result)
    ai_broll_summary = ai_image_gen.fill_broll_moments(
        broll_result,
        script,
        output_dir=OUT_DIR,
        budget=ai_budget,
        project_id=project_id,
        regenerate=regenerate_ai,
    )
    write_prompt_manifest(
        broll_result,
        script,
        OUT_DIR / "ai_prompt_manifest.json",
    )
    if project_id:
        write_prompt_manifest(
            broll_result,
            script,
            ENGINE_ROOT / "projects" / project_id / "ai_prompt_manifest.json",
        )
    cutout_summary = composite_assets.fill_cutouts(broll_result, dest_video, transcript)

    project_config = load_project_config(project_id) if project_id else {}

    script_id = Path((script or {}).get("filename_hint", "script")).stem
    custom_dest = PUBLIC_DIR / "custom_assets" / script_id
    if script and project_assets_dir:
        script, ai_custom_summary = ai_image_gen.ensure_custom_visual_assets(
            script,
            project_assets_dir,
            custom_dest,
        )
        _sync_custom_visual_shots(enriched_shot_list, script)
    else:
        ai_custom_summary = {"generated": 0, "cached": 0, "failed": 0, "cost_usd": 0.0}

    social_result = social_detector.detect(
        transcript,
        enriched_shot_list,
        script,
        project_config=project_config if project_config else None,
    )

    ai_cost_usd = round(
        float(ai_broll_summary.get("cost_usd", 0))
        + float(ai_custom_summary.get("cost_usd", 0))
        + float(cutout_summary.get("cost_usd", 0)),
        4,
    )
    ceiling = ai_cost_ceiling_usd()
    if ai_cost_usd > ceiling:
        raise RuntimeError(
            f"AI cost ${ai_cost_usd:.3f} exceeds hard ceiling ${ceiling:.2f}"
        )

    transcript_path = OUT_DIR / "transcript.json"
    shot_list_path = OUT_DIR / "shot_list.json"
    broll_path = OUT_DIR / "broll_moments.json"
    fun_path = OUT_DIR / "fun_moments.json"
    logo_path = OUT_DIR / "logo_moments.json"
    role_path = OUT_DIR / "role_moments.json"
    beats_path = OUT_DIR / "video_beats.json"
    step_beats_path = OUT_DIR / "step_beats.json"
    global_fx_path = OUT_DIR / "global_fx_moments.json"
    social_path = OUT_DIR / "social_moments.json"
    step_beats_result = step_beat_detector.detect(transcript, enriched_shot_list)

    (OUT_DIR / "render_props.json").write_text(json.dumps(render_props, indent=2))

    transcript_path.write_text(json.dumps(transcript, indent=2))
    save_srt(transcript, OUT_DIR / "captions.srt")
    broll_detector.save(broll_result, broll_path)
    fun_detector.save(fun_result, fun_path)
    logo_detector.save(logo_result, logo_path)
    role_caster.save(role_result, role_path)
    beat_detector.save(beats_result, beats_path)
    step_beat_detector.save(step_beats_result, step_beats_path)
    global_fx_detector.save(global_fx_result, global_fx_path)
    social_detector.save(social_result, social_path)

    lottie_warnings = lottie_assets.validate(OUT_DIR)
    for w in lottie_warnings:
        print(f"   ⚠️  Lottie: {w}")
    if not lottie_warnings:
        print("   Lottie assets OK")

    _stage_custom_assets(script, enriched_shot_list, project_assets_dir)
    shot_list_path.write_text(json.dumps(enriched_shot_list, indent=2))

    total_frames = transcript.get("total_frames", 300)
    est_render_mins = round((total_frames / 30) * 0.15, 1)

    summary = {
        "transcript_words": len(transcript.get("words", [])),
        "total_frames": total_frames,
        "shots_placed": len(enriched_shot_list.get("shots", [])),
        "broll_detected": broll_result["summary"]["detected"],
        "broll_types": broll_result["summary"]["types"],
        "broll_skipped": broll_result["summary"]["skipped"],
        "stock_fetched": stock_summary.get("fetched", 0),
        "stock_cached": stock_summary.get("cached", 0),
        "stock_failed": stock_summary.get("failed", 0),
        "stock_sources": stock_summary.get("sources", []),
        "jump_cuts": used_cut,
        "grade_applied": grade_applied or (not used_cut),
        "voice_enhanced": voice_applied,
        "music_track": music_config.get("file"),
        "fun_detected": len(fun_result.get("moments", [])),
        "fun_mood": fun_result["summary"]["mood"],
        "fun_types": fun_result["summary"]["types"],
        "fun_skipped": fun_result["summary"]["skipped"],
        "logos_detected": logo_result["summary"]["detected"],
        "logo_brands": logo_result["summary"]["brands"],
        "roles_detected": role_result["summary"]["detected"],
        "roles_cast": role_result["summary"]["roles"],
        "roles_skipped": role_result["summary"]["skipped"],
        "step_beats": step_beats_result["summary"]["count"],
        "step_numbers": step_beats_result["summary"]["steps"],
        "crust_frame": beats_result["crust_start"],
        "hook_end_frame": beats_result["hook_end"],
        "global_fx_detected": global_fx_result["summary"]["detected"],
        "global_fx_types": global_fx_result["summary"]["types"],
        "social_detected": social_result["summary"]["detected"],
        "social_types": social_result["summary"]["types"],
        "ai_images_generated": ai_broll_summary.get("generated", 0) + ai_custom_summary.get("generated", 0),
        "ai_images_cached": ai_broll_summary.get("cached", 0) + ai_custom_summary.get("cached", 0),
        "ai_images_failed": ai_broll_summary.get("failed", 0) + ai_custom_summary.get("failed", 0),
        "ai_cutouts_generated": cutout_summary.get("generated", 0),
        "ai_cutouts_cached": cutout_summary.get("cached", 0),
        "ai_cutouts_failed": cutout_summary.get("failed", 0),
        "ai_image_cost_usd": ai_cost_usd,
        "estimated_render_mins": est_render_mins,
    }

    if script:
        from src import trigger_audit
        audit_result = trigger_audit.audit(transcript, script)
        (OUT_DIR / "trigger_audit.json").write_text(json.dumps(audit_result, indent=2))
        summary["trigger_audit_passed"] = audit_result.get("passed")
        summary["trigger_match_rate"] = audit_result.get("match_rate")

    if project_id:
        checkpoint_shot_list(project_id, enriched_shot_list)
        write_input_props(project_id, render_props, transcript)
        sync_staging_to_public(OUT_DIR)

    print("   Staged: source.mp4, transcript.json, shot_list.json, broll_moments.json, fun_moments.json, logo_moments.json, role_moments.json, social_moments.json, step_beats.json, video_beats.json, global_fx_moments.json, render_props.json")
    print(
        f"   Shots: {summary['shots_placed']} | "
        f"B-roll: {summary['broll_detected']} detected, {summary['broll_skipped']} skipped | "
        f"Stock: {summary['stock_fetched']} fetched, {summary['stock_cached']} cached | "
        f"AI images: {summary['ai_images_generated']} new, {summary['ai_images_cached']} cached (${summary['ai_image_cost_usd']:.3f}) | "
        f"Social: {summary['social_detected']} ({', '.join(summary['social_types']) or 'none'}) | "
        f"Roles: {summary['roles_detected']} ({', '.join(summary['roles_cast']) or 'none'}) | "
        f"Fun FX: {summary['fun_detected']} | "
        f"Logos: {summary['logos_detected']} ({', '.join(summary['logo_brands']) or 'none'}) | "
        f"Step punches: {summary['step_beats']} ({', '.join(str(s) for s in summary['step_numbers']) or 'none'}) | "
        f"Jump cuts: {'yes' if used_cut else 'no'} | "
        f"Crust zoom @ {beats_result['summary']['crust_seconds']}s"
    )
    print(f"   Est. render: ~{summary['estimated_render_mins']} min")

    return summary
