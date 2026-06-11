from __future__ import annotations

"""
Podcast-style voice cleanup via ffmpeg audio filters.
Applied to source.mp4 before Remotion render.
"""

from src.pipeline_config import voice_denoise_strength, voice_enhance_enabled


def audio_filter_chain() -> str:
    """Light denoise + compression + presence EQ + social loudness."""
    nf = voice_denoise_strength()
    return ",".join(
        [
            "highpass=f=80",
            "lowpass=f=12000",
            f"afftdn=nf={nf}",
            "acompressor=threshold=-18dB:ratio=3:attack=5:release=50:makeup=2",
            "equalizer=f=250:t=q:w=1:g=-3",
            "equalizer=f=3000:t=q:w=1.5:g=2",
            "loudnorm=I=-16:TP=-1.5:LRA=11",
        ]
    )


def enabled() -> bool:
    return voice_enhance_enabled()
