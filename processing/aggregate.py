"""Geomean aggregation and HEK/HEPATOCYTE ratio table."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import gmean

from processing.constants import (
    CHEMSLUDGE_COL,
    DEFAULT_EXCLUDED_FROM_GEOMEAN,
    HEK_CELL_LINE,
    HEPATOCYTE_CELL_LINE,
)
from processing.transform import EC_IC_MEASUREMENTS

ARITHMETIC_MEAN_MEASUREMENTS = frozenset({"pAUC"})


def default_geomean_cell_lines(all_cell_lines: list[str]) -> list[str]:
    return [cl for cl in all_cell_lines if cl not in DEFAULT_EXCLUDED_FROM_GEOMEAN]


def compute_geomean_wide(
    wide_display: pd.DataFrame,
    selected_cell_lines: list[str],
    measurement: str | None = None,
) -> pd.Series:
    """Compute row-wise aggregate across selected cell line columns.

    Uses arithmetic mean for pAUC; geometric mean for all other measurements.
    """
    available = [cl for cl in selected_cell_lines if cl in wide_display.columns]
    if not available:
        return pd.Series(np.nan, index=wide_display.index, name="geomean")

    values = wide_display[available].astype(float)
    use_arithmetic = measurement in ARITHMETIC_MEAN_MEASUREMENTS

    def row_aggregate(row: pd.Series) -> float:
        valid = row.dropna()
        if valid.empty:
            return np.nan
        if use_arithmetic:
            return float(valid.mean())
        if (valid <= 0).any():
            return np.nan
        return float(gmean(valid))

    return values.apply(row_aggregate, axis=1).rename("geomean")


def build_ratio_table(
    wide_display: pd.DataFrame,
    wide_raw: pd.DataFrame,
    selected_cell_lines: list[str],
    measurement: str,
) -> pd.DataFrame:
    """Build final ratio table with HEK/HEPATOCYTE values and geomean ratios."""
    geomean = compute_geomean_wide(wide_display, selected_cell_lines, measurement)

    result = pd.DataFrame({CHEMSLUDGE_COL: wide_display[CHEMSLUDGE_COL], "geomean": geomean})

    unit_suffix = "_nM" if measurement in EC_IC_MEASUREMENTS else ""

    for cell_line, label in (
        (HEK_CELL_LINE, "HEKALOT9253"),
        (HEPATOCYTE_CELL_LINE, "HEPATOCYTE"),
    ):
        display_col = f"{label}{unit_suffix}"
        if cell_line in wide_display.columns:
            result[display_col] = wide_display[cell_line].values
        else:
            result[display_col] = np.nan

        if measurement in EC_IC_MEASUREMENTS:
            raw_col = f"{label}_raw_M"
            if cell_line in wide_raw.columns:
                result[raw_col] = wide_raw[cell_line].values
            else:
                result[raw_col] = np.nan

        ratio_col = f"{label} / geomean"
        if cell_line in wide_display.columns:
            ratio_values = wide_display[cell_line].values / geomean.values
            result[ratio_col] = ratio_values
            log2_col = f"log2({ratio_col})"
            with np.errstate(divide="ignore", invalid="ignore"):
                result[log2_col] = np.log2(ratio_values)
        else:
            result[ratio_col] = np.nan
            result[f"log2({ratio_col})"] = np.nan

    audit_cols = [cl for cl in wide_display.columns if cl != CHEMSLUDGE_COL]
    for col in audit_cols:
        result[col] = wide_display[col].values

    return result
