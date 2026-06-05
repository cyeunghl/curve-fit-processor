"""Streamlit app for curve-fit TSV processing."""

from __future__ import annotations

import io

import pandas as pd
import streamlit as st

from processing.aggregate import build_ratio_table, default_geomean_cell_lines
from processing.constants import CHEMSLUDGE_COL
from processing.parse import cell_line_tissue_map, ingest_tsv, list_cell_lines, list_measurements
from processing.transform import EC_IC_MEASUREMENTS, apply_transformations, pivot_measurement
from processing.visualize import create_measurement_heatmap
from ui.style import annotation_card, inject_styles

st.set_page_config(page_title="Curve Fit Processor", layout="wide")
inject_styles()

st.title("Curve Fit Processor")
st.caption("Upload a curve-fit TSV, select measurements and cell lines, review heatmaps and ratio tables.")

uploaded = st.file_uploader("Upload TSV or CSV", type=["tsv", "csv", "txt"])

if uploaded is None:
    st.markdown(
        annotation_card("Upload a standard curve-fit export to begin. Supported format: tab-separated with Chemsludge_Key and assay columns."),
        unsafe_allow_html=True,
    )
    st.stop()

sep = "\t" if uploaded.name.lower().endswith((".tsv", ".txt")) else ","
source = io.BytesIO(uploaded.getvalue())

try:
    raw_df = pd.read_csv(source, sep=sep)
    long_df = ingest_tsv(raw_df)
except ValueError as exc:
    st.error(str(exc))
    st.stop()

transformed = apply_transformations(long_df)
cell_lines = list_cell_lines(transformed)
measurements = list_measurements(transformed)
tissue_map = cell_line_tissue_map(long_df)

preferred = ["EC50", "EC90", "IC50", "Span", "aAUC", "pAUC"]
measurement_options = [m for m in preferred if m in measurements]
measurement_options.extend(m for m in measurements if m not in measurement_options)

default_selected = default_geomean_cell_lines(cell_lines)
heatmap_cell_lines = default_selected  # proliferation lines by default

tab_upload, tab_configure, tab_results = st.tabs(["Upload", "Configure", "Results"])

with tab_upload:
    st.markdown('<p class="section-label">File overview</p>', unsafe_allow_html=True)
    st.markdown(
        annotation_card(
            f"{raw_df[CHEMSLUDGE_COL].nunique()} compounds · "
            f"{len(cell_lines)} cell lines · "
            f"{len(measurements)} measurements detected"
        ),
        unsafe_allow_html=True,
    )
    meta_col1, meta_col2 = st.columns(2)
    with meta_col1:
        st.markdown(f"<span style='font-size:0.82rem;color:#666;'>Cell lines</span>", unsafe_allow_html=True)
        st.markdown(f"<span style='font-size:0.78rem;color:#888;'>{', '.join(cell_lines)}</span>", unsafe_allow_html=True)
    with meta_col2:
        st.markdown(f"<span style='font-size:0.82rem;color:#666;'>Measurements</span>", unsafe_allow_html=True)
        st.markdown(f"<span style='font-size:0.78rem;color:#888;'>{', '.join(measurements)}</span>", unsafe_allow_html=True)
    st.dataframe(raw_df.head(10), use_container_width=True, hide_index=True)

with tab_configure:
    st.markdown('<p class="section-label">Measurements</p>', unsafe_allow_html=True)
    selected_measurements = st.multiselect(
        "Select one or more measurements",
        measurement_options,
        default=[m for m in ["EC50", "EC90", "IC50"] if m in measurement_options] or measurement_options[:1],
        label_visibility="collapsed",
    )

    st.markdown('<p class="section-label">Cell lines for geomean</p>', unsafe_allow_html=True)
    st.markdown(
        annotation_card("HEKALOT9253 and HEPATOCYTE are unchecked by default. Heatmaps show proliferation lines unless toggled."),
        unsafe_allow_html=True,
    )

    selected_cell_lines: list[str] = []
    cols = st.columns(3)
    for idx, cell_line in enumerate(cell_lines):
        default_on = cell_line in default_selected
        with cols[idx % 3]:
            if st.checkbox(cell_line, value=default_on, key=f"cl_{cell_line}"):
                selected_cell_lines.append(cell_line)

    heatmap_cell_lines = selected_cell_lines or default_selected

    if not selected_measurements:
        st.warning("Select at least one measurement.")
    elif not selected_cell_lines:
        st.warning("Select at least one cell line for geomean calculation.")
    else:
        st.markdown('<p class="section-label">Heatmaps</p>', unsafe_allow_html=True)
        for measurement in selected_measurements:
            wide_display, _ = pivot_measurement(transformed, measurement)
            fig = create_measurement_heatmap(
                wide_display,
                measurement,
                tissue_map,
                cell_lines=heatmap_cell_lines,
            )
            st.pyplot(fig, clear_figure=True, use_container_width=True)

with tab_results:
    if not selected_measurements or not selected_cell_lines:
        st.info("Configure measurements and cell lines in the Configure tab.")
        st.stop()

    for measurement in selected_measurements:
        st.markdown(f'<div class="measurement-block">', unsafe_allow_html=True)
        st.markdown(f'<p class="section-label">{measurement}</p>', unsafe_allow_html=True)

        unit_label = "nM" if measurement in EC_IC_MEASUREMENTS else "native units"
        st.markdown(
            annotation_card(f"Ratio table · {unit_label} · log₂ ratios included for HEK and HEPATOCYTE"),
            unsafe_allow_html=True,
        )

        wide_display, wide_raw = pivot_measurement(transformed, measurement)
        ratio_table = build_ratio_table(
            wide_display, wide_raw, selected_cell_lines, measurement
        )

        primary_cols = [CHEMSLUDGE_COL, "geomean"]
        for label in ("HEKALOT9253", "HEPATOCYTE"):
            suffix = "_nM" if measurement in EC_IC_MEASUREMENTS else ""
            primary_cols.extend([
                f"{label}{suffix}",
                f"{label} / geomean",
                f"log2({label} / geomean)",
            ])
            if measurement in EC_IC_MEASUREMENTS:
                primary_cols.append(f"{label}_raw_M")

        primary_cols = [c for c in primary_cols if c in ratio_table.columns]
        st.dataframe(
            ratio_table[primary_cols].round(4),
            use_container_width=True,
            hide_index=True,
        )

        with st.expander("All cell-line values"):
            st.dataframe(wide_display.round(4), use_container_width=True, hide_index=True)

        ratio_csv = ratio_table.to_csv(index=False).encode("utf-8")
        wide_csv = wide_display.to_csv(index=False).encode("utf-8")

        dl_col1, dl_col2 = st.columns(2)
        with dl_col1:
            st.download_button(
                f"Download ratio table · {measurement}",
                data=ratio_csv,
                file_name=f"ratio_table_{measurement}.csv",
                mime="text/csv",
                key=f"dl_ratio_{measurement}",
            )
        with dl_col2:
            st.download_button(
                f"Download wide table · {measurement}",
                data=wide_csv,
                file_name=f"wide_{measurement}.csv",
                mime="text/csv",
                key=f"dl_wide_{measurement}",
            )

        st.markdown("</div>", unsafe_allow_html=True)
