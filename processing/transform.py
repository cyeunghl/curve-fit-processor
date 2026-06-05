"""Imputation rules and unit conversion for curve-fit values."""

from __future__ import annotations

import pandas as pd

from processing.constants import CHEMSLUDGE_COL

EC_IC_MEASUREMENTS = frozenset({"EC50", "EC90", "IC50"})
NM_MULTIPLIER = 1e9
IMPUTED_EC_IC_NM = 1000.0
IMPUTED_SPAN = 0.0
IMPUTED_AUC = 1.0


def _is_blank(value) -> bool:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def apply_transformations(long_df: pd.DataFrame) -> pd.DataFrame:
    """Apply imputation and nM conversion; add value_nm, value_raw_M, was_imputed."""
    df = long_df.copy()
    df["was_imputed"] = df["raw_value"].apply(_is_blank)

    def transform_row(row: pd.Series) -> pd.Series:
        measurement = row["measurement"]
        blank = row["was_imputed"]

        if measurement in EC_IC_MEASUREMENTS:
            if blank:
                return pd.Series(
                    {
                        "value_nm": IMPUTED_EC_IC_NM,
                        "value_raw_M": pd.NA,
                        "display_value": IMPUTED_EC_IC_NM,
                    }
                )
            raw_m = float(row["raw_value"])
            value_nm = raw_m * NM_MULTIPLIER
            return pd.Series(
                {
                    "value_nm": value_nm,
                    "value_raw_M": raw_m,
                    "display_value": value_nm,
                }
            )

        if measurement == "Span":
            display = IMPUTED_SPAN if blank else float(row["raw_value"])
            return pd.Series(
                {"value_nm": display, "value_raw_M": pd.NA, "display_value": display}
            )

        if measurement in {"aAUC", "pAUC"}:
            display = IMPUTED_AUC if blank else float(row["raw_value"])
            return pd.Series(
                {"value_nm": display, "value_raw_M": pd.NA, "display_value": display}
            )

        display = float(row["raw_value"]) if not blank else pd.NA
        return pd.Series(
            {"value_nm": display, "value_raw_M": pd.NA, "display_value": display}
        )

    transformed = df.join(df.apply(transform_row, axis=1))
    return transformed


def pivot_measurement(
    transformed_df: pd.DataFrame, measurement: str
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Pivot to wide format for display values and raw M (EC/IC only)."""
    subset = transformed_df[transformed_df["measurement"] == measurement]

    wide_display = subset.pivot(
        index=CHEMSLUDGE_COL, columns="cell_line", values="display_value"
    ).reset_index()

    wide_raw = subset.pivot(
        index=CHEMSLUDGE_COL, columns="cell_line", values="value_raw_M"
    ).reset_index()

    return wide_display, wide_raw
