"""
Main pipeline orchestrator.
Runs all steps in sequence with clear logging.
Each step is fault-tolerant — failure in one step
logs clearly rather than crashing silently.
"""

from __future__ import annotations

import time
from pathlib import Path

from dotenv import load_dotenv

ENGINE_ROOT = Path(__file__).resolve().parent
load_dotenv(ENGINE_ROOT.parent / ".env")
load_dotenv(ENGINE_ROOT / ".env")

from src import (  # noqa: E402
    asset_matcher,
    build_composition,
    caption_aligner,
    design_agent,
    fetch_scripts,
    matcher,
    notify,
    project_manager,
    render,
    shot_list_validate,
    shot_planner,
    transcribe,
)
from src.pipeline_config import use_design_agent  # noqa: E402
from src.project_paths import assets_dir, final_path, raw_path, transcript_path  # noqa: E402


def run(
    video_path: str,
    *,
    staging_only: bool = False,
    render_only: bool = False,
    from_stage: str | None = None,
    regenerate_ai: bool = False,
):
    start_time = time.time()
    original_path = Path(video_path).resolve()

    print(f"\n{'=' * 50}")
    print(f"🎬 Video Engine — {original_path.name}")
    print(f"{'=' * 50}\n")

    scripts = []
    transcript = None
    script = None
    shot_list = None
    output_path = None
    render_mins = 0.0
    project_id = None
    matched_assets: list[str] = []

    print("📡 Fetching scripts from GitHub...")
    try:
        scripts = fetch_scripts.get_recent(days=14)
    except Exception as e:
        print(f"   ❌ Script fetch failed: {e}")

    print("📁 Preparing project folder...")
    try:
        pre_match = project_manager.match_by_filename(original_path, scripts)
        project_id, project_root, video_path = project_manager.ingest_video(
            original_path,
            scripts=scripts,
            script=pre_match,
        )
        project_manager.init_meta(
            project_id,
            raw_original=original_path.name,
            script=pre_match,
        )
        print(f"   Project: projects/{project_id}/")
    except Exception as e:
        print(f"   ❌ Project setup failed: {e}")
        raise SystemExit(1) from e

    print("🎙️ Transcribing with faster-whisper...")
    try:
        tp = transcript_path(project_id)
        rp = Path(video_path)
        if render_only and tp.exists():
            import json
            transcript = json.loads(tp.read_text(encoding="utf-8"))
            print("   Render-only: reusing project transcript.json")
        elif tp.exists() and tp.stat().st_mtime > rp.stat().st_mtime:
            import json
            transcript = json.loads(tp.read_text(encoding="utf-8"))
            print("   Reusing cached transcript (newer than raw.mp4)")
        else:
            transcript = transcribe.run(
                video_path,
                transcript_dest=transcript_path(project_id),
            )
            project_manager.save_transcript(project_id, transcript)
    except Exception as e:
        print(f"   ❌ Transcription failed: {e}")
        raise SystemExit(1) from e

    print("🔍 Matching to script archive...")
    try:
        cfg = project_manager.load_project_config(project_id)
        if cfg.get("skip_archive_match"):
            print("   Project config: using local overrides (skip archive match)")
            script = None
        else:
            script = matcher.find(video_path, transcript, scripts)
    except Exception as e:
        print(f"   ❌ Matcher failed: {e}")

    script = project_manager.apply_project_config(project_id, script, transcript)

    if script:
        expected_id = project_manager.resolve_project_id(Path(video_path), script=script)
        if expected_id != project_id:
            print(f"   Renaming project {project_id} → {expected_id}")
            old_root = project_root
            project_id = expected_id
            project_root = project_manager.project_dir(project_id)
            if not project_root.exists():
                old_root.rename(project_root)
            video_path = str(project_manager.raw_path(project_id))
            script = project_manager.apply_project_config(project_id, script, transcript)

        project_manager.write_meta(
            project_id,
            title=script.get("title_overlay", ""),
            script_number=script.get("script_number"),
            matched_script_id=expected_id,
            custom_visual_overrides=script.get("custom_visual_overrides", []),
        )

        script, matched_assets = asset_matcher.resolve_overrides(
            script,
            assets_dir(project_id),
        )
        if matched_assets:
            print(f"   Custom assets auto-matched: {', '.join(matched_assets)}")

        if script.get("spoken_script"):
            print("📝 Aligning captions to script...")
            transcript = caption_aligner.align(transcript, script)

            from src import trigger_audit
            audit_result = trigger_audit.audit(transcript, script)
            if not audit_result.get("passed"):
                print("   ⚠️ Trigger audit below 90% — overlays may be sparse")

    print("🎨 Building shot list...")
    try:
        if script:
            shot_list = shot_planner.generate(transcript, script)
        elif use_design_agent():
            import os
            if os.getenv("ANTHROPIC_API_KEY"):
                shot_list = design_agent.generate(transcript, None)
            else:
                print("   No ANTHROPIC_API_KEY — using transcript planner")
                shot_list = shot_planner.generate(transcript, None)
        else:
            shot_list = shot_planner.generate(transcript, None)

        errors = shot_list_validate.validate(shot_list, transcript["total_frames"])
        if errors:
            print(f"   ⚠️ Shot list validation: {errors[0]}")
    except Exception as e:
        print(f"   ❌ Shot planning failed: {e}")
        print("   Falling back to captions-only render...")
        shot_list = design_agent.fallback_shot_list(transcript, script)

    if render_only:
        print("🎞️ Render-only: skipping staging, using remotion/public/")
        import json
        from src.build_composition import PUBLIC_DIR
        shot_list = json.loads((PUBLIC_DIR / "shot_list.json").read_text())
        staging_summary = {}
    else:
        print("🔧 Staging Remotion public/ assets...")
        staging_summary = {}
        try:
            staging_summary = build_composition.prepare(
                video_path,
                transcript,
                shot_list,
                script,
                project_assets_dir=assets_dir(project_id),
                regenerate_ai=regenerate_ai,
            )
        except Exception as e:
            print(f"   ❌ Composition staging failed: {e}")
            raise SystemExit(1) from e

    if staging_only:
        print("✅ Staging-only complete")
        return

    print("🎞️ Rendering final video...")
    render_start = time.time()
    try:
        output_path = render.run(
            video_path,
            shot_list,
            output_path=final_path(project_id),
        )
        render_mins = (time.time() - render_start) / 60
        print(f"   Rendered in {render_mins:.1f} minutes")
    except Exception as e:
        print(f"   ❌ Render failed: {e}")
        raise SystemExit(1) from e

    project_manager.mark_rendered(
        project_id,
        output_path=output_path,
        script=script,
        custom_assets_found=matched_assets,
        render_mins=render_mins,
    )
    if staging_summary:
        project_manager.write_meta(
            project_id,
            ai_image_cost_usd=staging_summary.get("ai_image_cost_usd", 0),
            ai_images_generated=staging_summary.get("ai_images_generated", 0),
            social_moments_detected=staging_summary.get("social_detected", 0),
        )

    print("📱 Sending Telegram notification...")
    try:
        notify.send(shot_list, script, output_path, render_mins)
    except Exception as e:
        print(f"   ❌ Notification failed: {e}")

    total_mins = (time.time() - start_time) / 60
    print(f"\n✅ Done in {total_mins:.1f} minutes")
    print(f"📁 {output_path}")
    print(f"📂 Project: projects/{project_id}/")
    if staging_summary:
        stock_fetched = staging_summary.get("stock_fetched", 0)
        stock_cached = staging_summary.get("stock_cached", 0)
        stock_sources = staging_summary.get("stock_sources", [])
        pexels_n = stock_sources.count("pexels")
        pixabay_n = stock_sources.count("pixabay")
        print(
            f"   Shots: {staging_summary.get('shots_placed', 0)} | "
            f"B-roll: {stock_fetched + stock_cached} stock clips "
            f"({pexels_n} Pexels, {pixabay_n} Pixabay) | "
            f"Roles: {staging_summary.get('roles_detected', 0)} | "
            f"Fun FX: {staging_summary.get('fun_detected', 0)} | "
            f"SFX: on | Grade: on"
        )
        print(f"   B-roll types: {', '.join(staging_summary.get('broll_types', [])) or 'none'}")
        print(f"   B-roll skipped: {staging_summary.get('broll_skipped', 0)}")
    print()
