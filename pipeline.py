"""
Main pipeline orchestrator.
Runs all steps in sequence with clear logging.
Each step is fault-tolerant — failure in one step
logs clearly rather than crashing silently.
"""

import time
from pathlib import Path

from dotenv import load_dotenv

ENGINE_ROOT = Path(__file__).resolve().parent
load_dotenv(ENGINE_ROOT.parent / ".env")
load_dotenv(ENGINE_ROOT / ".env")

from src import (  # noqa: E402
    build_composition,
    caption_aligner,
    design_agent,
    fetch_scripts,
    matcher,
    notify,
    render,
    shot_list_validate,
    shot_planner,
    transcribe,
)
from src.pipeline_config import use_design_agent  # noqa: E402


def run(video_path: str):
    start_time = time.time()
    video_path = str(Path(video_path).resolve())

    print(f"\n{'=' * 50}")
    print(f"🎬 Video Engine — {Path(video_path).name}")
    print(f"{'=' * 50}\n")

    scripts = []
    transcript = None
    script = None
    shot_list = None
    output_path = None
    render_mins = 0.0

    print("📡 Fetching scripts from GitHub...")
    try:
        scripts = fetch_scripts.get_recent(days=14)
    except Exception as e:
        print(f"   ❌ Script fetch failed: {e}")

    print("🎙️ Transcribing with faster-whisper...")
    try:
        transcript = transcribe.run(video_path)
    except Exception as e:
        print(f"   ❌ Transcription failed: {e}")
        raise SystemExit(1) from e

    print("🔍 Matching to script archive...")
    try:
        script = matcher.find(video_path, transcript, scripts)
    except Exception as e:
        print(f"   ❌ Matcher failed: {e}")

    if script:
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

    print("🔧 Staging Remotion public/ assets...")
    staging_summary = {}
    try:
        staging_summary = build_composition.prepare(video_path, transcript, shot_list, script)
    except Exception as e:
        print(f"   ❌ Composition staging failed: {e}")
        raise SystemExit(1) from e

    print("🎞️ Rendering final video...")
    render_start = time.time()
    try:
        output_path = render.run(video_path, shot_list)
        render_mins = (time.time() - render_start) / 60
        print(f"   Rendered in {render_mins:.1f} minutes")
    except Exception as e:
        print(f"   ❌ Render failed: {e}")
        raise SystemExit(1) from e

    print("📱 Sending Telegram notification...")
    try:
        notify.send(shot_list, script, output_path, render_mins)
    except Exception as e:
        print(f"   ❌ Notification failed: {e}")

    total_mins = (time.time() - start_time) / 60
    print(f"\n✅ Done in {total_mins:.1f} minutes")
    print(f"📁 {output_path}")
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
