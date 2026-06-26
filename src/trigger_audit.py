from __future__ import annotations

"""
Post-alignment audit: verify script-defined triggers match the transcript.
Surfaces silent overlay drops before render.
"""

from src.trigger_utils import phrase_in_transcript, resolve_phrase_frame


def _match_phrase(words: list, full_text: str, phrase: str) -> bool:
    return phrase_in_transcript(words, full_text, phrase)


def audit(transcript: dict, script: dict | None, *, strict: bool = False) -> dict:
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

    for i, phrase in enumerate(triggers.get("broll_phrases") or []):
        if phrase:
            checks.append({"field": f"broll_phrases[{i}]", "phrase": phrase})

    for i, entry in enumerate(triggers.get("logo_phrases") or []):
        if isinstance(entry, dict) and entry.get("phrase"):
            checks.append({"field": f"logo_phrases[{i}]", "phrase": entry["phrase"]})

    for i, phrase in enumerate(triggers.get("global_fx_phrases") or []):
        if phrase:
            checks.append({"field": f"global_fx_phrases[{i}]", "phrase": phrase})

    for i, stat in enumerate(triggers.get("stat_phrases") or []):
        if isinstance(stat, dict) and stat.get("phrase"):
            checks.append({"field": f"stat_phrases[{i}]", "phrase": stat["phrase"]})

    for i, moment in enumerate(script.get("visual_moments") or []):
        if isinstance(moment, dict) and moment.get("at_phrase"):
            checks.append({"field": f"visual_moments[{i}]", "phrase": moment["at_phrase"]})

    validation_errors: list[str] = []
    broll_phrases = triggers.get("broll_phrases") or []
    broll_descs = triggers.get("broll_image_descriptions") or []
    if broll_phrases:
        if len(broll_descs) != len(broll_phrases):
            validation_errors.append(
                f"broll_image_descriptions length {len(broll_descs)} != broll_phrases {len(broll_phrases)}"
            )
        for i, phrase in enumerate(broll_phrases):
            if phrase and (i >= len(broll_descs) or not broll_descs[i]):
                validation_errors.append(f"missing broll_image_descriptions[{i}] for '{phrase[:40]}'")

    matches: list[dict] = []
    misses: list[dict] = []

    for check in checks:
        phrase = check["phrase"]
        frame, method = resolve_phrase_frame(words, full_text, phrase)
        if frame is not None:
            matches.append({**check, "frame": frame, "method": method})
        else:
            misses.append(check)

    total = len(checks)
    rate = len(matches) / total if total else 1.0
    passed = len(misses) == 0 and not validation_errors if strict else (
        rate >= 0.9 or (total <= 2 and len(misses) == 0)
    ) and not validation_errors

    result = {
        "passed": passed,
        "match_rate": round(rate, 3),
        "total_checks": total,
        "matched": len(matches),
        "matches": matches,
        "misses": misses,
        "validation_errors": validation_errors,
    }

    if validation_errors:
        preview = "; ".join(validation_errors[:3])
        print(f"   ⚠️ Trigger audit validation: {preview}")

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
