"""Shared ingestion pipeline: parse -> map -> validate -> clean."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.ingestion.cleaner import CleanOutcome, clean
from app.ingestion.mapper import apply_mapping, check_mapping
from app.ingestion.parser import read_upload
from app.ingestion.validator import ValidationReport, validate


def run_validation(
    df_raw: pd.DataFrame, mapping: dict[str, str]
) -> tuple[pd.DataFrame, ValidationReport]:
    df_mapped = apply_mapping(df_raw, mapping)
    return df_mapped, validate(df_mapped)


def run_cleaning(df_mapped: pd.DataFrame, report: ValidationReport) -> CleanOutcome:
    return clean(df_mapped, report)


def load_raw_frame(path: Path, sheet: str | None) -> tuple[pd.DataFrame, list[str] | None]:
    df, sheets, _ = read_upload(path, sheet)
    return df, sheets


def mapping_problems(mapping: dict[str, str], available: list[str]) -> list[str]:
    return check_mapping(mapping, available)
