"""
Triggers Remotion render via CLI.
Reads staged files from remotion/public/ — no input-props.json.
"""

import shutil
import subprocess
from pathlib import Path
from typing import Optional, Union

ENGINE_ROOT = Path(__file__).resolve().parent.parent
REMOTION_DIR = ENGINE_ROOT / "remotion"
PUBLIC_DIR = REMOTION_DIR / "public"
OUTPUT_DIR = ENGINE_ROOT / "ready_to_post"
REMOTION_OUT = REMOTION_DIR / "out" / "video.mp4"


def _verify_staged() -> None:
    required = ["source.mp4", "transcript.json", "shot_list.json", "broll_moments.json"]
    missing = [f for f in required if not (PUBLIC_DIR / f).exists()]
    if missing:
        raise FileNotFoundError(f"Missing staged files in public/: {missing}")


def run(video_path: str, shot_list: dict, output_path: Optional[Union[str, Path]] = None) -> str:
    _verify_staged()
    REMOTION_OUT.parent.mkdir(parents=True, exist_ok=True)

    if output_path is None:
        OUTPUT_DIR.mkdir(exist_ok=True)
        video_stem = Path(video_path).stem
        safe_title = "".join(
            c if c.isalnum() or c in "-_" else "_" for c in shot_list.get("video_title", video_stem)
        )[:60]
        output_path = OUTPUT_DIR / f"{safe_title}_{video_stem}.mp4"
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

    base_cmd = [
        "remotion",
        "render",
        "src/index.ts",
        "VideoComposition",
        str(REMOTION_OUT),
        "--log=verbose",
    ]

    result = None
    for runner in (["bunx"], ["npx"]):
        cmd = runner + base_cmd
        result = subprocess.run(cmd, cwd=REMOTION_DIR, capture_output=True, text=True)
        if result.returncode == 0:
            break
        if "not found" in (result.stderr or "").lower() or result.returncode == 127:
            continue
        break

    if result is None or result.returncode != 0:
        print("   Remotion render stderr:")
        print(result.stderr[-3000:] if result and result.stderr else "(empty)")
        raise RuntimeError(f"Remotion render failed with code {result.returncode if result else -1}")

    if not REMOTION_OUT.exists():
        raise FileNotFoundError(f"Expected output not found: {REMOTION_OUT}")

    shutil.copy2(REMOTION_OUT, output_path)
    print(f"   Output: {output_path}")
    return str(output_path.resolve())
