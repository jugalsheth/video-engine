from __future__ import annotations

from pathlib import Path

ENGINE_ROOT = Path(__file__).resolve().parent.parent
RULES_DIR = ENGINE_ROOT / "rules"

# fun_type -> (keywords, min_mood_tier)  tier 0=medium, 1=chaos
CHAOS_FUN_TYPES = {"manga_lines", "fire_spark"}


def load_arrow_map(filename: str) -> dict[str, list[str]]:
    """Parse 'key → a, b, c' rule files."""
    path = RULES_DIR / filename
    mapping: dict[str, list[str]] = {}
    if not path.exists():
        return mapping
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "→" not in line:
            continue
        key, vals = line.split("→", 1)
        keywords = [v.strip() for v in vals.split(",") if v.strip()]
        if keywords:
            mapping[key.strip()] = keywords
    return mapping


def load_fun_groups() -> dict[str, tuple[list[str], int]]:
    raw = load_arrow_map("fun_animation_map.txt")
    groups: dict[str, tuple[list[str], int]] = {}
    for fun_type, keywords in raw.items():
        tier = 1 if fun_type in CHAOS_FUN_TYPES else 0
        groups[fun_type] = (keywords, tier)
    return groups


def load_role_keywords() -> dict[str, list[str]]:
    return load_arrow_map("role_cast_map.txt")


def load_logo_map() -> dict[str, dict]:
    """Parse logo_map.txt → {brand_id: {file, aliases, label}}."""
    path = RULES_DIR / "logo_map.txt"
    mapping: dict[str, dict] = {}
    if not path.exists():
        return mapping
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "→" not in line:
            continue
        left, right = line.split("→", 1)
        brand_id = left.strip()
        parts = [p.strip() for p in right.split("|")]
        file_name = parts[0] if parts else f"{brand_id}.svg"
        aliases = [brand_id]
        if len(parts) > 1 and parts[1]:
            aliases.extend(a.strip() for a in parts[1].split(",") if a.strip())
        label_overrides = {
            "anthropic": "Claude",
            "githubcopilot": "GitHub Copilot",
            "amazonaws": "AWS",
            "apachekafka": "Kafka",
            "meta": "Meta",
            "langchain": "LangChain",
            "llamaindex": "LlamaIndex",
        }
        mapping[brand_id] = {
            "file": file_name,
            "aliases": list(dict.fromkeys(aliases)),
            "label": label_overrides.get(brand_id, brand_id.replace("_", " ").title()),
        }
    return mapping
