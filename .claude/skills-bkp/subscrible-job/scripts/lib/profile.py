"""Profile loading and persistence."""
import json
import os
from typing import Any


def load_profile(path: str) -> dict[str, Any]:
    """Load profile JSON from file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_profile(path: str, profile: dict[str, Any]) -> None:
    """Save profile JSON to file."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)
        f.write("\n")


def update_extra_fields(
    profile_path: str,
    new_fields: dict[str, str],
) -> tuple[int, int]:
    """Merge new fields into profile's extra_fields and save."""
    with open(profile_path, "r", encoding="utf-8") as f:
        profile = json.load(f)

    profile.setdefault("extra_fields", {})

    added = 0
    updated = 0
    for key, value in new_fields.items():
        if not value:
            continue
        if key in profile["extra_fields"]:
            if profile["extra_fields"][key] != value:
                profile["extra_fields"][key] = value
                updated += 1
        else:
            profile["extra_fields"][key] = value
            added += 1

    save_profile(profile_path, profile)
    return added, updated


def add_learned_field(
    profile_path: str,
    label: str,
    value: str,
) -> None:
    """Record a learned field mapping for future runs."""
    with open(profile_path, "r", encoding="utf-8") as f:
        profile = json.load(f)

    profile.setdefault("learned_fields", {})
    profile["learned_fields"][label.lower()] = {
        "last_value": value,
        "keyword_hint": label.split()[0] if label else "",
    }

    save_profile(profile_path, profile)