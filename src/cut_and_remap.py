from __future__ import annotations

import json
import subprocess
from pathlib import Path

from src.media_process import GRADE_FILTER

FPS = 30


def _remap_frame(old_frame: int, frame_map: list[tuple[int, int]]) -> int:
    for orig, new in frame_map:
        if orig == old_frame:
            return new
    best = 0
    for orig, new in frame_map:
        if orig <= old_frame:
            best = new
        else:
            break
    return best


def _build_frame_map(kept_segments: list[dict], fps: int = FPS) -> tuple[list[tuple[int, int]], int]:
    mapping: list[tuple[int, int]] = []
    new_frame = 0
    for seg in kept_segments:
        start_f = int(seg["start_s"] * fps)
        end_f = int(seg["end_s"] * fps)
        for orig in range(start_f, end_f):
            mapping.append((orig, new_frame))
            new_frame += 1
    return mapping, new_frame


def _remap_json(data: dict, frame_map: list[tuple[int, int]], total_frames: int) -> dict:
    if "words" in data:
        words = []
        for w in data["words"]:
            nf = _remap_frame(w["start_frame"], frame_map)
            ne = _remap_frame(w["end_frame"], frame_map)
            if nf >= total_frames:
                continue
            words.append({
                **w,
                "start_frame": nf,
                "end_frame": min(ne, total_frames - 1),
                "start": round(nf / FPS, 3),
                "end": round(min(ne, total_frames - 1) / FPS, 3),
            })
        data["words"] = words
        data["full_text"] = " ".join(w["word"] for w in words)
        data["total_frames"] = total_frames
        data["duration_seconds"] = round(total_frames / FPS, 2)
        return data

    if "shots" in data:
        for shot in data["shots"]:
            shot["start_frame"] = _remap_frame(shot["start_frame"], frame_map)
            shot["end_frame"] = min(_remap_frame(shot["end_frame"], frame_map), total_frames)
        data["total_frames"] = total_frames
        return data

    if "moments" in data:
        new_moments = []
        for m in data["moments"]:
            ns = _remap_frame(m["start_frame"], frame_map)
            ne = min(_remap_frame(m["end_frame"], frame_map), total_frames)
            if ns < total_frames:
                new_moments.append({**m, "start_frame": ns, "end_frame": ne})
        data["moments"] = new_moments
        return data

    for key in ("hook_end", "crust_start", "hook_start"):
        if key in data:
            data[key] = _remap_frame(int(data[key]), frame_map)
    return data


def _concat_segments(source: Path, kept: list[dict], dest: Path, work_dir: Path) -> None:
    work_dir.mkdir(parents=True, exist_ok=True)
    segment_files: list[Path] = []
    for i, seg in enumerate(kept):
        seg_path = work_dir / f"seg_{i}.mp4"
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-ss", str(seg["start_s"]),
                "-to", str(seg["end_s"]),
                "-i", str(source),
                "-vf", GRADE_FILTER,
                "-c:a", "aac", "-b:a", "128k",
                str(seg_path),
            ],
            capture_output=True,
            check=True,
        )
        segment_files.append(seg_path)

    if len(segment_files) == 1:
        segment_files[0].rename(dest)
        return

    list_file = work_dir / "concat.txt"
    with list_file.open("w") as f:
        for p in segment_files:
            f.write(f"file '{p.resolve()}'\n")

    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(dest)],
        capture_output=True,
        check=True,
    )
    for p in segment_files:
        p.unlink(missing_ok=True)
    list_file.unlink(missing_ok=True)


def apply_jump_cuts(
    source_video: Path,
    dest_video: Path,
    silence_map: dict,
    public_dir: Path,
    transcript: dict,
    shot_list: dict,
    broll: dict,
    fun: dict,
    logos: dict,
    roles: dict,
    beats: dict,
) -> tuple[dict, dict, dict, dict, dict, dict, dict, int]:
    kept = silence_map.get("kept_segments", [])
    if len(kept) <= 1 and silence_map.get("removed_total_s", 0) < 0.1:
        return transcript, shot_list, broll, fun, logos, roles, beats, transcript["total_frames"]

    try:
        _concat_segments(source_video, kept, dest_video, public_dir / "cut_work")
    except subprocess.CalledProcessError as e:
        print(f"   Jump cut failed, using uncut video: {e}")
        return transcript, shot_list, broll, fun, logos, roles, beats, transcript["total_frames"]

    frame_map, total_frames = _build_frame_map(kept)
    (public_dir / "frame_map.json").write_text(
        json.dumps({"map": frame_map, "total_frames": total_frames}, indent=2)
    )

    transcript = _remap_json(transcript, frame_map, total_frames)
    shot_list = _remap_json(shot_list, frame_map, total_frames)
    broll = _remap_json(broll, frame_map, total_frames)
    fun = _remap_json(fun, frame_map, total_frames)
    logos = _remap_json(logos, frame_map, total_frames)
    roles = _remap_json(roles, frame_map, total_frames)
    beats = _remap_json(beats, frame_map, total_frames)

    print(f"   Jump cuts: removed {silence_map.get('removed_total_s', 0)}s → {total_frames} frames")
    return transcript, shot_list, broll, fun, logos, roles, beats, total_frames
