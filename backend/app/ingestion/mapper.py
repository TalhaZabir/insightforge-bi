"""Column mapping: suggestions from header aliases + requirement checks."""

from __future__ import annotations

from app.ingestion.aliases import (
    ALIAS_MAP,
    CANONICAL_FIELDS,
    REQUIRED_GROUPS,
    REQUIRED_SINGLETONS,
    normalize_header,
)


def suggest_mapping(columns: list[str]) -> dict[str, str]:
    """Returns {canonical: original_column} for recognized headers."""
    mapping: dict[str, str] = {}
    used: set[str] = set()
    for col in columns:
        canon = ALIAS_MAP.get(normalize_header(col))
        if canon and canon not in mapping and col not in used:
            mapping[canon] = col
            used.add(col)
    return mapping


def check_mapping(mapping: dict[str, str], available: list[str]) -> list[str]:
    """Returns a list of human-readable problems (empty = OK)."""
    problems: list[str] = []
    unknown = [c for c in CANONICAL_FIELDS if c in mapping and mapping[c] not in available]
    for c in unknown:
        problems.append(f"Mapped column '{mapping[c]}' for '{c}' is not in the file")
    for field in REQUIRED_SINGLETONS:
        if field not in mapping:
            problems.append(f"Required field '{field}' is not mapped")
    for group in REQUIRED_GROUPS:
        if not any(g in mapping for g in group):
            problems.append(f"One of {list(group)} must be mapped")
    for canon in mapping:
        if canon not in CANONICAL_FIELDS:
            problems.append(f"Unknown canonical field '{canon}'")
    return problems


def apply_mapping(df_raw, mapping: dict[str, str]):
    """Renames mapped columns to canonical names; keeps only mapped columns."""

    frame = df_raw.copy()
    rename = {orig: canon for canon, orig in mapping.items() if orig in frame.columns}
    frame = frame.rename(columns=rename)
    keep = [c for c in CANONICAL_FIELDS if c in frame.columns]
    out = frame[keep].copy()
    out["_row_num"] = range(2, len(out) + 2)  # 1-based incl. header row
    return out
