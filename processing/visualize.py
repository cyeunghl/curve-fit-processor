"""Minimal heatmap visualizations for curve-fit data."""

from __future__ import annotations

from io import BytesIO

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.patches import Patch

from processing.constants import CHEMSLUDGE_COL
from processing.transform import EC_IC_MEASUREMENTS

# Soft muted tissue palette
TISSUE_COLORS: dict[str, str] = {
    "Bladder/Urinary Tract": "#B8A9C9",
    "Breast": "#D4A5A5",
    "Esophagus/Stomach": "#C4B896",
    "Lung": "#8FBFB3",
    "Scalp": "#A8B5C4",
    "Liver": "#C9A882",
}
DEFAULT_TISSUE_COLOR = "#D8D8D4"

# Soft diverging heatmap: muted rose → warm white → muted blue
HEATMAP_CMAP = mcolors.LinearSegmentedColormap.from_list(
    "muted_diverging",
    ["#D4A0A0", "#F7F4F0", "#A0B8C8"],
)


def _heatmap_values(wide_display: pd.DataFrame, measurement: str) -> pd.DataFrame:
    """Convert wide display values to heatmap scale (-log10 M for EC/IC)."""
    data = wide_display.set_index(CHEMSLUDGE_COL).copy()
    if measurement in EC_IC_MEASUREMENTS:
        with np.errstate(divide="ignore", invalid="ignore"):
            data = -np.log10(data.astype(float) / 1e9)
    else:
        data = data.astype(float)
    return data


def _ordered_columns(
    columns: list[str], tissue_map: dict[str, str]
) -> list[str]:
    return sorted(columns, key=lambda cl: (tissue_map.get(cl, ""), cl))


def _short_label(cell_line: str) -> str:
    return f"{cell_line} (CTG)"


def create_measurement_heatmap(
    wide_display: pd.DataFrame,
    measurement: str,
    tissue_map: dict[str, str],
    cell_lines: list[str] | None = None,
) -> Figure:
    """Build a minimal tissue-annotated heatmap for one measurement."""
    available = [cl for cl in (cell_lines or list(wide_display.columns)) if cl != CHEMSLUDGE_COL and cl in wide_display.columns]
    if not available:
        fig, ax = plt.subplots(figsize=(6, 2))
        ax.text(0.5, 0.5, "No data", ha="center", va="center", fontsize=9, color="#888")
        ax.axis("off")
        return fig

    ordered = _ordered_columns(available, tissue_map)
    plot_df = _heatmap_values(wide_display, measurement)[ordered]

    n_rows, n_cols = plot_df.shape
    cell_w, cell_h = 0.72, 0.55
    fig_w = max(5.5, n_cols * cell_w + 2.8)
    fig_h = max(2.8, n_rows * cell_h + 1.8)

    fig = plt.figure(figsize=(fig_w, fig_h), facecolor="white")
    gs = fig.add_gridspec(
        2, 2,
        height_ratios=[0.08, 1],
        width_ratios=[1, 0.06],
        hspace=0.04,
        wspace=0.06,
        left=0.14,
        right=0.88,
        top=0.88,
        bottom=0.22,
    )

    ax_bar = fig.add_subplot(gs[0, 0])
    ax_heat = fig.add_subplot(gs[1, 0])
    ax_cbar = fig.add_subplot(gs[1, 1])

    # Tissue annotation bar
    for idx, cl in enumerate(ordered):
        tissue = tissue_map.get(cl, "")
        color = TISSUE_COLORS.get(tissue, DEFAULT_TISSUE_COLOR)
        ax_bar.add_patch(
            plt.Rectangle((idx, 0), 1, 1, facecolor=color, edgecolor="none", alpha=0.85)
        )
    ax_bar.set_xlim(0, n_cols)
    ax_bar.set_ylim(0, 1)
    ax_bar.axis("off")

    # Heatmap
    vals = plot_df.values.astype(float)
    im = ax_heat.imshow(
        vals,
        aspect="auto",
        cmap=HEATMAP_CMAP,
        vmin=np.nanpercentile(vals, 5) if np.any(~np.isnan(vals)) else 0,
        vmax=np.nanpercentile(vals, 95) if np.any(~np.isnan(vals)) else 1,
    )

    ax_heat.set_xticks(range(n_cols))
    ax_heat.set_xticklabels(
        [_short_label(cl) for cl in ordered],
        rotation=90,
        fontsize=7,
        color="#555",
        fontfamily="sans-serif",
    )
    ax_heat.set_yticks(range(n_rows))
    ax_heat.set_yticklabels(
        plot_df.index.tolist(),
        fontsize=7,
        color="#555",
        fontfamily="sans-serif",
    )
    ax_heat.tick_params(length=0, pad=4)
    for spine in ax_heat.spines.values():
        spine.set_visible(False)

    # Cell annotations
    for i in range(n_rows):
        for j in range(n_cols):
            val = vals[i, j]
            if np.isnan(val):
                continue
            ax_heat.text(
                j, i, f"{val:.1f}",
                ha="center", va="center",
                fontsize=6, color="#444", fontfamily="sans-serif",
            )

    # Colorbar
    unit = "-log10 M" if measurement in EC_IC_MEASUREMENTS else measurement
    cbar = fig.colorbar(im, cax=ax_cbar)
    cbar.ax.tick_params(labelsize=6, length=2, color="#aaa", labelcolor="#666")
    cbar.outline.set_visible(False)

    # Title
    fig.suptitle(
        f"{measurement} ({unit})",
        fontsize=10,
        color="#333",
        fontweight="500",
        fontfamily="sans-serif",
        y=0.97,
    )

    # Tissue legend
    tissues_in_plot = []
    for cl in ordered:
        t = tissue_map.get(cl, "")
        if t and t not in tissues_in_plot:
            tissues_in_plot.append(t)

    if tissues_in_plot:
        handles = [
            Patch(
                facecolor=TISSUE_COLORS.get(t, DEFAULT_TISSUE_COLOR),
                edgecolor="none",
                alpha=0.85,
                label=t,
            )
            for t in tissues_in_plot
        ]
        leg = fig.legend(
            handles=handles,
            loc="center left",
            bbox_to_anchor=(0.91, 0.55),
            frameon=False,
            fontsize=6,
            labelcolor="#666",
            handlelength=1.2,
            handleheight=0.5,
        )
        for text in leg.get_texts():
            text.set_fontfamily("sans-serif")

    return fig


def fig_to_bytes(fig: Figure) -> bytes:
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=150, facecolor="white", bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()
