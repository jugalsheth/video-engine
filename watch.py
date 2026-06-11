"""
Folder watcher. Two modes:

Mode 1 — Watch folder (automatic):
  python watch.py
  Watches raw_videos/ for new MP4 files.
  Triggers pipeline automatically on new file.

Mode 2 — Single file (manual test):
  python watch.py --file raw_videos/script_01_career.mp4
  Runs pipeline once on the specified file.
  Use this for your first trial run.
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


class VideoHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith(".mp4"):
            print(f"\n📂 New file detected: {event.src_path}")
            time.sleep(3)
            pipeline.run(event.src_path)


def watch_folder():
    raw_dir = ENGINE_ROOT / "raw_videos"
    raw_dir.mkdir(exist_ok=True)
    observer = Observer()
    observer.schedule(VideoHandler(), str(raw_dir), recursive=False)
    observer.start()
    print("👁️  Watching raw_videos/ for new MP4 files...")
    print("    Drop a video to start the pipeline.")
    print("    Ctrl+C to stop.\n")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


def run_single(file_path: str):
    path = Path(file_path)
    if not path.is_absolute():
        path = ENGINE_ROOT / path
    if not path.exists():
        print(f"❌ File not found: {path}")
        sys.exit(1)
    pipeline.run(str(path))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", help="Run pipeline on a single file")
    args = parser.parse_args()

    if args.file:
        run_single(args.file)
    else:
        watch_folder()
