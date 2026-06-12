from __future__ import annotations

"""
Stages per-video assets into remotion/public/ for Remotion to consume.
"""

import json
import shutil
from pathlib import Path

from src import beat_detector, broll_detector, fetch_broll, fetch_music, fun_detector, logo_detector, lottie_assets, role_caster, step_beat_detector
from src.render_props import resolve_render_props
from src.template_loader import resolve_template
from src.trigger_audit import preferred_pause_seconds
from src.visual_scheduler import apply_template_to_shots, fill_fun_gaps, enforce_min_visual_events
from src.caption_converter import save_srt
from src.cut_and_remap import apply_jump_cuts
from src.detect_silence import detect as detect_silence
from src.media_process import finalize_source_video
from src.pipeline_config import jump_cuts_enabled
from src import voice_enhance

ENGINE_ROOT = Path(__file__).resolve().parent.parent
PUBLIC_DIR = ENGINE_ROOT / "remotion" / "public"
BRAND_CONFIG_PATH = ENGINE_ROOT / "rules" / "brand_config.json"


def _load_brand_config() -> dict:
    if not BRAND_CONFIG_PATH.exists():
        return {}
    return json.loads(BRAND_CONFIG_PATH.read_text(encoding="utf-8"))

def prepare(
    video_path: str,
    transcript: dict,
    shot_list: dict,
    script: dict | None = None,
) -> dict:
    video_path = Path(video_path).resolve()
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)

    dest_video = PUBLIC_DIR / "source.mp4"
    dest_cut = PUBLIC_DIR / "source_cut.mp4"

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

    broll_result = broll_detector.detect(transcript, enriched_shot_list, script)
    fun_result = fun_detector.detect(transcript, enriched_shot_list, script)
    fun_result = fill_fun_gaps(transcript, enriched_shot_list, fun_result, broll_result, template)
    fun_result = enforce_min_visual_events(
        transcript, enriched_shot_list, fun_result, broll_result, template,
    )
    logo_result = logo_detector.detect(transcript, enriched_shot_list, script)
    role_result = role_caster.detect(transcript, enriched_shot_list)
    beats_result = beat_detector.detect(transcript, script)

    used_cut = False
    if jump_cuts_enabled():
        try:
            pause_hints = preferred_pause_seconds(script)
            silence_map = detect_silence(video_path, preferred_pause_seconds=pause_hints or None)
            (PUBLIC_DIR / "silence_map.json").write_text(json.dumps(silence_map, indent=2))
            if silence_map.get("removed_total_s", 0) >= 0.1:
                transcript, enriched_shot_list, broll_result, fun_result, logo_result, role_result, beats_result, _ = (
                    apply_jump_cuts(
                        video_path,
                        dest_cut,
                        silence_map,
                        PUBLIC_DIR,
                        transcript,
                        enriched_shot_list,
                        broll_result,
                        fun_result,
                        logo_result,
                        role_result,
                        beats_result,
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

    transcript_path = PUBLIC_DIR / "transcript.json"
    shot_list_path = PUBLIC_DIR / "shot_list.json"
    broll_path = PUBLIC_DIR / "broll_moments.json"
    fun_path = PUBLIC_DIR / "fun_moments.json"
    logo_path = PUBLIC_DIR / "logo_moments.json"
    role_path = PUBLIC_DIR / "role_moments.json"
    beats_path = PUBLIC_DIR / "video_beats.json"
    step_beats_path = PUBLIC_DIR / "step_beats.json"
    step_beats_result = step_beat_detector.detect(transcript, enriched_shot_list)

    render_props = resolve_render_props(script, brand_config)
    (PUBLIC_DIR / "render_props.json").write_text(json.dumps(render_props, indent=2))

    transcript_path.write_text(json.dumps(transcript, indent=2))
    save_srt(transcript, PUBLIC_DIR / "captions.srt")
    shot_list_path.write_text(json.dumps(enriched_shot_list, indent=2))
    broll_detector.save(broll_result, broll_path)
    fun_detector.save(fun_result, fun_path)
    logo_detector.save(logo_result, logo_path)
    role_caster.save(role_result, role_path)
    beat_detector.save(beats_result, beats_path)
    step_beat_detector.save(step_beats_result, step_beats_path)

    lottie_warnings = lottie_assets.validate(PUBLIC_DIR)
    for w in lottie_warnings:
        print(f"   ⚠️  Lottie: {w}")
    if not lottie_warnings:
        print("   Lottie assets OK")

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
        "estimated_render_mins": est_render_mins,
    }

    if script:
        from src import trigger_audit
        audit_result = trigger_audit.audit(transcript, script)
        (PUBLIC_DIR / "trigger_audit.json").write_text(json.dumps(audit_result, indent=2))
        summary["trigger_audit_passed"] = audit_result.get("passed")
        summary["trigger_match_rate"] = audit_result.get("match_rate")

    print("   Staged: source.mp4, transcript.json, shot_list.json, broll_moments.json, fun_moments.json, logo_moments.json, role_moments.json, step_beats.json, video_beats.json, render_props.json")
    print(
        f"   Shots: {summary['shots_placed']} | "
        f"B-roll: {summary['broll_detected']} detected, {summary['broll_skipped']} skipped | "
        f"Stock: {summary['stock_fetched']} fetched, {summary['stock_cached']} cached | "
        f"Roles: {summary['roles_detected']} ({', '.join(summary['roles_cast']) or 'none'}) | "
        f"Fun FX: {summary['fun_detected']} | "
        f"Logos: {summary['logos_detected']} ({', '.join(summary['logo_brands']) or 'none'}) | "
        f"Step punches: {summary['step_beats']} ({', '.join(str(s) for s in summary['step_numbers']) or 'none'}) | "
        f"Jump cuts: {'yes' if used_cut else 'no'} | "
        f"Crust zoom @ {beats_result['summary']['crust_seconds']}s"
    )
    print(f"   Est. render: ~{summary['estimated_render_mins']} min")

    return summary
