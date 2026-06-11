"""
Transcribes a video file using faster-whisper locally.
Free. Runs on CPU. Word-level timestamps for frame-accurate animation.
"""

import json
import os
import re
import subprocess
from pathlib import Path

from faster_whisper import WhisperModel

from src.pipeline_config import whisper_model

FPS = 30
ENGINE_ROOT = Path(__file__).resolve().parent.parent


def _punctuate(full_text: str) -> str:
    text = full_text.strip()
    if text and text[-1] not in ".!?":
        text += "."
    text = re.sub(r"\s+i'm\b", " I'm", text, flags=re.I)
    text = re.sub(r"\s+i've\b", " I've", text, flags=re.I)
    return text


def run(video_path: str) -> dict:
    """
    Transcribes video and returns structured transcript
    with word-level frame numbers.
    """
    video_path = Path(video_path).resolve()
    model_name = whisper_model()

    audio_path = video_path.with_suffix(".wav")
    subprocess.run(
        [
            "ffmpeg",
            "-i",
            str(video_path),
            "-ar",
            "16000",
            "-ac",
            "1",
            "-y",
            str(audio_path),
        ],
        capture_output=True,
        check=True,
    )

    print(f"   Audio extracted: {audio_path.name}")
    print(f"   Whisper model: {model_name}")

    model = WhisperModel(model_name, device="cpu", compute_type="int8")

    segments, info = model.transcribe(
        str(audio_path),
        word_timestamps=True,
    )

    words = []
    for segment in segments:
        for word in segment.words:
            words.append(
                {
                    "word": word.word.strip(),
                    "start": round(word.start, 3),
                    "end": round(word.end, 3),
                    "start_frame": int(word.start * FPS),
                    "end_frame": int(word.end * FPS),
                }
            )

    duration = words[-1]["end"] if words else 0
    total_frames = int(duration * FPS) + 30

    full_text = _punctuate(" ".join(w["word"] for w in words))

    transcript = {
        "full_text": full_text,
        "words": words,
        "duration_seconds": round(duration, 2),
        "total_frames": total_frames,
        "fps": FPS,
    }

    transcript_path = video_path.parent / f"{video_path.stem}_transcript.json"
    transcript_path.write_text(json.dumps(transcript, indent=2))

    audio_path.unlink(missing_ok=True)

    print(
        f"   Transcribed: {len(words)} words, "
        f"{duration:.1f}s, {total_frames} frames"
    )

    return transcript
