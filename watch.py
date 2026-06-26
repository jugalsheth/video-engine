"""
Folder watcher. Two modes:

Mode 1 — Watch folder (automatic):
  python watch.py
  Watches inbox/ for new MP4 files.
  Triggers pipeline automatically on new file.

Mode 2 — Single file or project (manual):
  python watch.py --file inbox/script_03_kafka.mp4
  python watch.py --project script_03_kafka_hiring
  python watch.py --project script_01 --staging-only
  python watch.py --project script_01 --render-only
  Runs pipeline once on the specified file or project raw.mp4.
"""

import argparse
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

ENGINE_ROOT = Path(__file__).resolve().parent
load_dotenv(ENGINE_ROOT.parent / ".env")
load_dotenv(ENGINE_ROOT / ".env")

import pipeline  # noqa: E402
from src.project_manager import ensure_dirs  # noqa: E402
from src.project_paths import INBOX_DIR, raw_path  # noqa: E402


class VideoHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith(".mp4"):
            print(f"\n📂 New file detected: {event.src_path}")
            time.sleep(3)
            pipeline.run(event.src_path)


def watch_folder():
    ensure_dirs()
    observer = Observer()
    observer.schedule(VideoHandler(), str(INBOX_DIR), recursive=False)
    observer.start()
    print("👁️  Watching inbox/ for new MP4 files...")
    print("    Drop a video to start the pipeline.")
    print("    Finished videos land in projects/{name}/final.mp4")
    print("    Ctrl+C to stop.\n")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


def run_single(file_path: str, **kwargs):
    path = Path(file_path)
    if not path.is_absolute():
        path = ENGINE_ROOT / path
    if not path.exists():
        print(f"❌ File not found: {path}")
        sys.exit(1)
    pipeline.run(str(path), **kwargs)


def run_project(project_id: str, **kwargs):
    path = raw_path(project_id)
    if not path.exists():
        print(f"❌ No raw.mp4 in projects/{project_id}/")
        print("    Drop your recording in inbox/ first, or add raw.mp4 to the project folder.")
        sys.exit(1)
    pipeline.run(str(path), **kwargs)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", help="Run pipeline on a single file (inbox/ or legacy path)")
    parser.add_argument("--project", help="Re-render projects/{id}/raw.mp4")
    parser.add_argument("--staging-only", action="store_true", help="Run through staging, skip render")
    parser.add_argument("--render-only", action="store_true", help="Render from existing remotion/public/")
    parser.add_argument("--from-stage", choices=["transcribe", "match", "shots", "stage", "render"])
    parser.add_argument("--regenerate-ai", action="store_true", help="Clear and regenerate AI b-roll images")
    args = parser.parse_args()

    stage_kwargs = {
        "staging_only": args.staging_only,
        "render_only": args.render_only,
        "from_stage": args.from_stage,
        "regenerate_ai": args.regenerate_ai,
    }

    if args.file:
        run_single(args.file, **stage_kwargs)
    elif args.project:
        run_project(args.project, **stage_kwargs)
    else:
        watch_folder()
