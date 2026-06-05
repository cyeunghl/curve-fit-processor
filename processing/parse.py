"""Parse curve-fit TSV column headers and reshape to long format."""

from __future__ import annotations

import io
import re
from typing import BinaryIO

import pandas as pd

from processing.constants import CHEMSLUDGE_COL

COLUMN_RE = re.compile(r"\('([^']+)',\s*'([^']+)'\)_(\w+)$")
METADATA_COLUMNS = {CHEMSLUDGE_COL, "SMILES"}


def parse_column_name(column: str) -> tuple[str, str, str] | None:
    """Return (tissue, cell_line, measurement) or None for non-assay columns."""
    match = COLUMN_RE.match(column)
    if not match:
        return None
    tissue, cell_descriptor, measurement = match.groups()
    cell_line = cell_descriptor.split(" (")[0].strip()
    return tissue, cell_line, measurement


def ingest_tsv(source: str | BinaryIO | io.BytesIO | pd.DataFrame, sep: str = "\t") -> pd.DataFrame:
    """Read TSV/CSV and return long-format DataFrame with raw values."""
    if isinstance(source, pd.DataFrame):
        df = source
    else:
        df = pd.read_csv(source, sep=sep)

    if CHEMSLUDGE_COL not in df.columns:
        raise ValueError(f"Expected column '{CHEMSLUDGE_COL}' in uploaded file.")

    records: list[dict] = []
    for column in df.columns:
        if column in METADATA_COLUMNS:
            continue
        parsed = parse_column_name(column)
        if parsed is None:
            continue
        _tissue, cell_line, measurement = parsed
        for chemsludge, raw_value in zip(df[CHEMSLUDGE_COL], df[column]):
            records.append(
                {
                    CHEMSLUDGE_COL: chemsludge,
                    "tissue": _tissue,
                    "cell_line": cell_line,
                    "measurement": measurement,
                    "raw_value": raw_value,
                }
            )

    if not records:
        raise ValueError("No assay columns matching expected nomenclature were found.")

    return pd.DataFrame.from_records(records)


def list_cell_lines(long_df: pd.DataFrame) -> list[str]:
    return sorted(long_df["cell_line"].unique())


def list_measurements(long_df: pd.DataFrame) -> list[str]:
    return sorted(long_df["measurement"].unique())


def cell_line_tissue_map(long_df: pd.DataFrame) -> dict[str, str]:
    """Return mapping of cell_line -> tissue (first occurrence)."""
    mapping: dict[str, str] = {}
    for _, row in long_df.drop_duplicates("cell_line").iterrows():
        mapping[row["cell_line"]] = row["tissue"]
    return mapping
