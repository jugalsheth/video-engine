from __future__ import annotations

import subprocess
from pathlib import Path

from src import voice_enhance

GRADE_FILTER = "eq=contrast=1.08:brightness=0.02:saturation=1.05"


def finalize_source_video(
    source: Path,
    dest: Path,
    *,
    apply_grade: bool = True,
    apply_voice: bool | None = None,
) -> None:
    """Grade and/or enhance voice on the talking-head source track."""
    if apply_voice is None:
        apply_voice = voice_enhance.enabled()

    if not apply_grade and not apply_voice:
        if source.resolve() != dest.resolve():
            dest.write_bytes(source.read_bytes())
        return

    cmd = ["ffmpeg", "-y", "-i", str(source)]

    if apply_grade:
        cmd.extend(["-vf", GRADE_FILTER])
        cmd.extend(["-c:v", "libx264", "-preset", "fast", "-crf", "18"])
    else:
        cmd.extend(["-c:v", "copy"])

    if apply_voice:
        cmd.extend(["-af", voice_enhance.audio_filter_chain()])
        cmd.extend(["-c:a", "aac", "-b:a", "192k"])
    else:
        cmd.extend(["-c:a", "copy"])

    cmd.append(str(dest))
    subprocess.run(cmd, capture_output=True, check=True)
