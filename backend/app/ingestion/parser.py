"""File parsing: CSV (encoding/delimiter tolerant) and XLSX (multi-sheet)."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path

import pandas as pd

CSV_ENCODINGS = ["utf-8-sig", "utf-8", "cp1252", "latin1"]


class SheetRequiredError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def list_sheets(path: Path) -> list[str] | None:
    if path.suffix.lower() in (".xlsx", ".xls"):
        import openpyxl

        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        return wb.sheetnames
    return None


def _sniff_delimiter(sample: str) -> str:
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
    except csv.Error:
        return ","


def read_csv_tolerant(path: Path) -> tuple[pd.DataFrame, str]:
    raw = path.read_bytes()
    text_sample = None
    encoding_used = "utf-8-sig"
    for enc in CSV_ENCODINGS:
        try:
            text_sample = raw.decode(enc)
            encoding_used = enc
            break
        except (UnicodeDecodeError, LookupError):
            continue
    if text_sample is None:
        raise ValueError("Could not decode CSV with supported encodings")
    delimiter = _sniff_delimiter(text_sample[:100_000])
    df = pd.read_csv(
        path,
        dtype=str,
        keep_default_na=False,
        encoding=encoding_used,
        delimiter=delimiter,
        engine="python",
    )
    df.columns = [str(c).strip() for c in df.columns]
    return df, encoding_used


def read_upload(
    path: Path, sheet: str | None = None
) -> tuple[pd.DataFrame, list[str] | None, str | None]:
    """Returns (dataframe, sheets_or_None, encoding_or_None)."""
    suffix = path.suffix.lower()
    if suffix == ".csv":
        df, enc = read_csv_tolerant(path)
        return df, None, enc
    if suffix in (".xlsx", ".xls"):
        sheets = list_sheets(path) or []
        if sheet is None:
            if len(sheets) == 1:
                sheet = sheets[0]
            else:
                raise SheetRequiredError(f"Workbook has sheets {sheets}; choose one")
        if sheet not in sheets:
            raise ValueError(f"Sheet '{sheet}' not found in {sheets}")
        df = pd.read_excel(path, sheet_name=sheet, dtype=str, keep_default_na=False)
        df.columns = [str(c).strip() for c in df.columns]
        return df, sheets, None
    raise ValueError(f"Unsupported file type: {suffix}")
