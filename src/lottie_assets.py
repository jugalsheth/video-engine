from __future__ import annotations

from pathlib import Path

ENGINE_ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ENGINE_ROOT / "remotion" / "public"
MIN_BYTES = 500

# First existing file > MIN_BYTES wins
FUN_LOTTIES: dict[str, list[str]] = {
    "confetti": ["lottie/fun/confetti.json"],
    "money_rain": ["lottie/fun/money_rain.json"],
    "fire_spark": ["lottie/fun/fire_burst.json", "lottie/fun/fire_spark.json"],
    "mind_blown": ["lottie/fun/mind_blown.json"],
    "checkmark_pop": ["lottie/fun/checkmark_pop.json"],
}

STAT_LOTTIES: list[str] = [
    "lottie/fun/sparkle_burst.json",
    "lottie/fun/datapulse.json",
    "lottie/data_pulse.json",
    "lottie/chart_growth.json",
]


def resolve(public_dir: Path, candidates: list[str]) -> str | None:
    for rel in candidates:
        path = public_dir / rel
        if path.exists() and path.stat().st_size >= MIN_BYTES:
            return rel
    return None


def fun_lottie_map(public_dir: Path | None = None) -> dict[str, str]:
    base = public_dir or PUBLIC
    out: dict[str, str] = {}
    for key, candidates in FUN_LOTTIES.items():
        resolved = resolve(base, candidates)
        if resolved:
            out[key] = resolved
    return out


def stat_lottie_file(public_dir: Path | None = None) -> str:
    base = public_dir or PUBLIC
    return resolve(base, STAT_LOTTIES) or "lottie/chart_growth.json"


def validate(public_dir: Path | None = None) -> list[str]:
    """Returns warning lines for missing or empty Lottie files."""
    base = public_dir or PUBLIC
    warnings: list[str] = []
    all_expected = set()
    for candidates in FUN_LOTTIES.values():
        all_expected.update(candidates)
    all_expected.update(STAT_LOTTIES)

    for rel in sorted(all_expected):
        path = base / rel
        if not path.exists():
            warnings.append(f"missing: {rel}")
        elif path.stat().st_size < MIN_BYTES:
            warnings.append(f"empty/corrupt ({path.stat().st_size}B): {rel} — re-download from LottieFiles")

    return warnings
