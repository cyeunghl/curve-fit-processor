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
RAW_RATIO_SUM_MEASUREMENTS = frozenset({"pAUC", "aAUC"})
LOG2_RATIO_SUM_MEASUREMENTS = EC_IC_MEASUREMENTS


def aggregate_column_name(measurement: str) -> str:
    """Column label for the row-wise aggregate (mean for pAUC, geomean otherwise)."""
    return "mean" if measurement in ARITHMETIC_MEAN_MEASUREMENTS else "geomean"


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
    col_name = aggregate_column_name(measurement) if measurement else "geomean"
    available = [cl for cl in selected_cell_lines if cl in wide_display.columns]
    if not available:
        return pd.Series(np.nan, index=wide_display.index, name=col_name)

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

    return values.apply(row_aggregate, axis=1).rename(col_name)


def ratio_sum_column_name(measurement: str) -> str | None:
    """Return sum column label for supported measurements, else None."""
    if measurement in LOG2_RATIO_SUM_MEASUREMENTS:
        return "sum log2 ratios"
    if measurement in RAW_RATIO_SUM_MEASUREMENTS:
        return "sum ratios"
    return None


def add_ratio_sum_column(result: pd.DataFrame, measurement: str) -> pd.DataFrame:
    """Add per-row sum of HEK + HEPATOCYTE ratios (log2 for EC/IC, raw for pAUC/aAUC)."""
    sum_col = ratio_sum_column_name(measurement)
    if sum_col is None:
        return result

    agg_col = aggregate_column_name(measurement)
    if measurement in LOG2_RATIO_SUM_MEASUREMENTS:
        hek_col = f"log2(HEKALOT9253 / {agg_col})"
        hep_col = f"log2(HEPATOCYTE / {agg_col})"
    else:
        hek_col = f"HEKALOT9253 / {agg_col}"
        hep_col = f"HEPATOCYTE / {agg_col}"

    result = result.copy()
    result[sum_col] = result[hek_col].astype(float) + result[hep_col].astype(float)
    return result


def build_ratio_table(
    wide_display: pd.DataFrame,
    wide_raw: pd.DataFrame,
    selected_cell_lines: list[str],
    measurement: str,
    *,
    include_ratio_sum: bool = False,
) -> pd.DataFrame:
    """Build final ratio table with HEK/HEPATOCYTE values and aggregate ratios."""
    agg_col = aggregate_column_name(measurement)
    aggregate = compute_geomean_wide(wide_display, selected_cell_lines, measurement)

    result = pd.DataFrame({CHEMSLUDGE_COL: wide_display[CHEMSLUDGE_COL], agg_col: aggregate})

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

        ratio_col = f"{label} / {agg_col}"
        if cell_line in wide_display.columns:
            ratio_values = wide_display[cell_line].values / aggregate.values
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

    if include_ratio_sum:
        result = add_ratio_sum_column(result, measurement)

    return result
