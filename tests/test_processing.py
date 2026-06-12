"""Tests for curve-fit TSV processing pipeline."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.stats import gmean

from processing.aggregate import (
    build_ratio_table,
    compute_geomean_wide,
    default_geomean_cell_lines,
)
from processing.constants import CHEMSLUDGE_COL, HEK_CELL_LINE
from processing.parse import cell_line_tissue_map, ingest_tsv, list_cell_lines, list_measurements
from processing.transform import (
    IMPUTED_EC_IC_NM,
    apply_transformations,
    pivot_measurement,
)

SAMPLE_TSV = Path(__file__).parent.parent / "curve_fit_data (1).tsv"


@pytest.fixture
def pipeline_data():
    long_df = ingest_tsv(SAMPLE_TSV)
    transformed = apply_transformations(long_df)
    return long_df, transformed


def test_ingest_parses_cell_lines_and_measurements(pipeline_data):
    long_df, _ = pipeline_data
    cell_lines = list_cell_lines(long_df)
    measurements = list_measurements(long_df)

    assert "CALU6" in cell_lines
    assert "HEKALOT9253" in cell_lines
    assert "HEPATOCYTES_HUMAN_LOT_240604" in cell_lines
    assert measurements == ["EC50", "EC90", "IC50", "Span", "aAUC", "pAUC"]


def test_ec50_nm_conversion(pipeline_data):
    _, transformed = pipeline_data
    row = transformed[
        (transformed[CHEMSLUDGE_COL] == "HB-48711")
        & (transformed["cell_line"] == "CALU6")
        & (transformed["measurement"] == "EC50")
    ].iloc[0]

    assert not row["was_imputed"]
    assert row["value_raw_M"] == pytest.approx(1.1071524864010244e-09)
    assert row["display_value"] == pytest.approx(1.1071524864010244)


def test_blank_ec50_imputed_to_1000_nm(pipeline_data):
    _, transformed = pipeline_data
    row = transformed[
        (transformed[CHEMSLUDGE_COL] == "HB-44333")
        & (transformed["cell_line"] == "CALU6")
        & (transformed["measurement"] == "EC50")
    ].iloc[0]

    assert row["was_imputed"]
    assert row["display_value"] == IMPUTED_EC_IC_NM
    assert pd.isna(row["value_raw_M"])


def test_blank_span_imputed_to_zero(pipeline_data):
    _, transformed = pipeline_data
    row = transformed[
        (transformed[CHEMSLUDGE_COL] == "HB-44333")
        & (transformed["cell_line"] == "CALU6")
        & (transformed["measurement"] == "Span")
    ].iloc[0]

    assert row["was_imputed"]
    assert row["display_value"] == 0.0


def test_default_geomean_excludes_hek_and_hepatocyte(pipeline_data):
    _, transformed = pipeline_data
    cell_lines = list_cell_lines(transformed)
    default = default_geomean_cell_lines(cell_lines)

    assert HEK_CELL_LINE not in default
    assert "HEPATOCYTES_HUMAN_LOT_240604" not in default
    assert "CALU6" in default
    assert "KPL4" in default


def test_ratio_table_has_expected_columns(pipeline_data):
    _, transformed = pipeline_data
    cell_lines = list_cell_lines(transformed)
    selected = default_geomean_cell_lines(cell_lines)

    wide_display, wide_raw = pivot_measurement(transformed, "EC50")
    ratio_table = build_ratio_table(wide_display, wide_raw, selected, "EC50")

    assert "geomean" in ratio_table.columns
    assert "HEKALOT9253_nM" in ratio_table.columns
    assert "HEKALOT9253_raw_M" in ratio_table.columns
    assert "HEKALOT9253 / geomean" in ratio_table.columns
    assert "HEPATOCYTE_nM" in ratio_table.columns
    assert "HEPATOCYTE / geomean" in ratio_table.columns
    assert "log2(HEKALOT9253 / geomean)" in ratio_table.columns
    assert "log2(HEPATOCYTE / geomean)" in ratio_table.columns

    hb48711 = ratio_table[ratio_table[CHEMSLUDGE_COL] == "HB-48711"].iloc[0]
    assert hb48711["HEKALOT9253_nM"] == pytest.approx(6.424520856582594)
    assert hb48711["geomean"] > 0
    assert hb48711["HEKALOT9253 / geomean"] == pytest.approx(
        hb48711["HEKALOT9253_nM"] / hb48711["geomean"]
    )
    assert hb48711["log2(HEKALOT9253 / geomean)"] == pytest.approx(
        np.log2(hb48711["HEKALOT9253 / geomean"])
    )


def test_pauc_uses_arithmetic_mean(pipeline_data):
    _, transformed = pipeline_data
    cell_lines = list_cell_lines(transformed)
    selected = default_geomean_cell_lines(cell_lines)

    wide_display, wide_raw = pivot_measurement(transformed, "pAUC")
    row = wide_display[wide_display[CHEMSLUDGE_COL] == "HB-48711"].iloc[0]

    values = [float(row[cl]) for cl in selected if cl in wide_display.columns]
    expected_mean = float(np.mean(values))

    aggregate = compute_geomean_wide(wide_display, selected, "pAUC")
    hb48711_idx = wide_display[wide_display[CHEMSLUDGE_COL] == "HB-48711"].index[0]
    assert aggregate.loc[hb48711_idx] == pytest.approx(expected_mean)

    # geomean would differ from arithmetic mean for this compound
    assert float(gmean(values)) != pytest.approx(expected_mean)


def test_cell_line_tissue_map(pipeline_data):
    long_df, _ = pipeline_data
    mapping = cell_line_tissue_map(long_df)
    assert mapping["CALU6"] == "Lung"
    assert mapping["KPL4"] == "Breast"
    assert mapping["HEKALOT9253"] == "Scalp"
