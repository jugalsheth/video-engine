from __future__ import annotations

"""
Post-alignment audit: verify script-defined triggers match the transcript.
Surfaces silent overlay drops before render.
"""

from src.frame_utils import frame_for_phrase, fuzzy_frame_for_phrase, normalize


def _match_phrase(words: list, full_text: str, phrase: str) -> bool:
    if not phrase:
        return True
    if frame_for_phrase(words, full_text, phrase) is not None:
        return True
    return fuzzy_frame_for_phrase(words, phrase) is not None


def audit(transcript: dict, script: dict | None) -> dict:
    if not script:
        return {"passed": True, "matches": [], "misses": [], "match_rate": 1.0}

    words = transcript.get("words", [])
    full_text = transcript.get("full_text", "")
    triggers = script.get("video_triggers") or {}

    checks: list[dict] = []

    beats = triggers.get("beat_phrases") or {}
    for label, phrase in (
        ("beat_phrases.crust", beats.get("crust")),
        ("beat_phrases.payoff", beats.get("payoff")),
    ):
        if phrase:
            checks.append({"field": label, "phrase": phrase})

    for i, phrase in enumerate(triggers.get("fun_phrases") or []):
        if phrase:
            checks.append({"field": f"fun_phrases[{i}]", "phrase": phrase})

    for i, stat in enumerate(triggers.get("stat_phrases") or []):
        if isinstance(stat, dict) and stat.get("phrase"):
            checks.append({"field": f"stat_phrases[{i}]", "phrase": stat["phrase"]})

    for i, moment in enumerate(script.get("visual_moments") or []):
        if isinstance(moment, dict) and moment.get("at_phrase"):
            checks.append({"field": f"visual_moments[{i}]", "phrase": moment["at_phrase"]})

    matches: list[dict] = []
    misses: list[dict] = []

    for check in checks:
        phrase = check["phrase"]
        if _match_phrase(words, full_text, phrase):
            matches.append(check)
        else:
            misses.append(check)

    total = len(checks)
    rate = len(matches) / total if total else 1.0
    passed = rate >= 0.9 or (total <= 2 and len(misses) == 0)

    result = {
        "passed": passed,
        "match_rate": round(rate, 3),
        "total_checks": total,
        "matched": len(matches),
        "matches": matches,
        "misses": misses,
    }

    if misses:
        preview = ", ".join(f"{m['field']}: '{m['phrase'][:30]}'" for m in misses[:4])
        print(f"   ⚠️ Trigger audit: {len(misses)}/{total} missed — {preview}")
    else:
        print(f"   ✅ Trigger audit: {len(matches)}/{total} matched")

    return result


def preferred_pause_seconds(script: dict | None) -> list[float]:
    """Extract second targets from recording_cues with PAUSE actions."""
    if not script:
        return []
    seconds: list[float] = []
    for cue in script.get("recording_cues") or []:
        action = (cue.get("action") or "").upper()
        if "PAUSE" in action and cue.get("second") is not None:
            try:
                seconds.append(float(cue["second"]))
            except (TypeError, ValueError):
                pass
    return seconds
