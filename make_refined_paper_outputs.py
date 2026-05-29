"""Create paper-ready refined-scan figures, tables, and captions.

This script is intentionally post-processing only. It reads the locally generated
refined CSV files for the 0.85--1.05 s period window and writes paper-ready
figures/caption assets without running Capytaine or changing any physical or
normalization assumptions.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ARRAY_SIZES = (4, 6, 8)
OUTPUT_DIR = Path("outputs")
FIGURE_DIR = Path("figures")
PERIOD_WINDOW_LABEL = "0p85_1p05"
PERIOD_WINDOW_TEXT = "0.85--1.05 s"

SUMMARY_PATHS = {
    array_size: OUTPUT_DIR
    / f"N{array_size}_refined_period_scan_summary_{PERIOD_WINDOW_LABEL}.csv"
    for array_size in ARRAY_SIZES
}
PEAK_TABLE_PATH = OUTPUT_DIR / f"N468_refined_center_peak_table_{PERIOD_WINDOW_LABEL}.csv"

MEAN_FIGURE_PATH = FIGURE_DIR / f"N468_refined_center_mean_{PERIOD_WINDOW_LABEL}_paper.png"
MAX_FIGURE_PATH = FIGURE_DIR / f"N468_refined_center_max_{PERIOD_WINDOW_LABEL}_paper.png"
COMBINED_FIGURE_PATH = (
    FIGURE_DIR / f"N468_refined_center_response_{PERIOD_WINDOW_LABEL}_paper_combined.png"
)
PAPER_PEAK_TABLE_PATH = OUTPUT_DIR / "N468_refined_center_peak_table_for_paper.csv"
CAPTIONS_PATH = OUTPUT_DIR / "N468_refined_figure_table_captions.md"

SUMMARY_REQUIRED_COLUMNS = {"array_size", "period", "center_mean_abs", "center_max_abs"}
PEAK_REQUIRED_COLUMNS = {"array_size", "metric", "peak_value", "peak_period"}
METRIC_LABELS = {
    "A_c_mean": "Mean centre amplitude",
    "A_c_max": "Maximum centre amplitude",
    "R_loc": "Local centre max/mean ratio",
}
PLOT_STYLES = {
    4: {"marker": "o", "linestyle": "-"},
    6: {"marker": "s", "linestyle": "--"},
    8: {"marker": "^", "linestyle": "-."},
}


@dataclass(frozen=True)
class MetricSpec:
    """Plot metadata for one centre-response metric."""

    column: str
    ylabel: str
    title: str
    output_path: Path


MEAN_SPEC = MetricSpec(
    column="center_mean_abs",
    ylabel=r"Mean centre amplitude $A_{c,mean}$",
    title="Refined centre mean response",
    output_path=MEAN_FIGURE_PATH,
)
MAX_SPEC = MetricSpec(
    column="center_max_abs",
    ylabel=r"Maximum centre amplitude $A_{c,max}$",
    title="Refined centre maximum response",
    output_path=MAX_FIGURE_PATH,
)


def ensure_output_directories() -> None:
    """Create output directories for locally generated paper assets."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    FIGURE_DIR.mkdir(exist_ok=True)


def require_columns(dataframe: pd.DataFrame, required_columns: set[str], path: Path) -> None:
    """Raise a helpful error if a CSV lacks required columns."""
    missing = sorted(required_columns - set(dataframe.columns))
    if missing:
        raise ValueError(f"{path} is missing required columns: {missing}")


def read_summary(array_size: int, path: Path) -> pd.DataFrame:
    """Read and validate one refined period-scan summary table."""
    if not path.exists():
        raise FileNotFoundError(
            f"Missing refined summary CSV for N={array_size}: {path}. "
            "Run the refined scan locally before creating paper outputs."
        )

    summary = pd.read_csv(path)
    require_columns(summary, SUMMARY_REQUIRED_COLUMNS, path)
    summary = summary.copy()
    summary["array_size"] = pd.to_numeric(summary["array_size"], errors="raise").astype(int)
    summary["period"] = pd.to_numeric(summary["period"], errors="raise")
    summary["center_mean_abs"] = pd.to_numeric(summary["center_mean_abs"], errors="raise")
    summary["center_max_abs"] = pd.to_numeric(summary["center_max_abs"], errors="raise")

    unexpected_sizes = sorted(set(summary["array_size"]) - {array_size})
    if unexpected_sizes:
        raise ValueError(
            f"{path} contains array_size values that do not match N={array_size}: "
            f"{unexpected_sizes}"
        )

    return summary.sort_values("period", ignore_index=True)


def read_all_summaries() -> dict[int, pd.DataFrame]:
    """Read all N=4/6/8 refined summary CSV files."""
    return {
        array_size: read_summary(array_size, path)
        for array_size, path in SUMMARY_PATHS.items()
    }


def read_peak_table() -> pd.DataFrame:
    """Read the locally generated refined centre peak table."""
    if not PEAK_TABLE_PATH.exists():
        raise FileNotFoundError(
            f"Missing refined peak table CSV: {PEAK_TABLE_PATH}. "
            "Create the refined peak table locally before creating paper outputs."
        )

    peak_table = pd.read_csv(PEAK_TABLE_PATH)
    require_columns(peak_table, PEAK_REQUIRED_COLUMNS, PEAK_TABLE_PATH)
    peak_table = peak_table.copy()
    peak_table["array_size"] = pd.to_numeric(peak_table["array_size"], errors="raise").astype(int)
    peak_table["peak_period"] = pd.to_numeric(peak_table["peak_period"], errors="raise")
    peak_table["peak_value"] = pd.to_numeric(peak_table["peak_value"], errors="raise")
    return peak_table.sort_values(["array_size", "metric"], ignore_index=True)


def add_metric_lines(ax: plt.Axes, summaries: dict[int, pd.DataFrame], spec: MetricSpec) -> None:
    """Add N=4/6/8 centre-response curves to an axis."""
    for array_size, summary in summaries.items():
        style = PLOT_STYLES[array_size]
        ax.plot(
            summary["period"],
            summary[spec.column],
            label=f"N={array_size}",
            linewidth=1.6,
            markersize=4.0,
            marker=style["marker"],
            linestyle=style["linestyle"],
        )
    ax.set_xlim(0.85, 1.05)
    ax.set_xlabel("Wave period T (s)")
    ax.set_ylabel(spec.ylabel)
    ax.set_title(spec.title)
    ax.grid(True, alpha=0.30, linewidth=0.7)
    ax.legend(title="Array size", frameon=False)


def save_single_metric_figure(summaries: dict[int, pd.DataFrame], spec: MetricSpec) -> None:
    """Save one paper-ready metric figure."""
    fig, ax = plt.subplots(figsize=(6.8, 4.2), constrained_layout=True)
    add_metric_lines(ax, summaries, spec)
    fig.savefig(spec.output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved figure: {spec.output_path}")


def save_combined_figure(summaries: dict[int, pd.DataFrame]) -> None:
    """Save a two-panel paper-ready centre-response figure."""
    fig, axes = plt.subplots(2, 1, figsize=(7.0, 7.2), sharex=True, constrained_layout=True)
    add_metric_lines(axes[0], summaries, MEAN_SPEC)
    add_metric_lines(axes[1], summaries, MAX_SPEC)
    axes[0].set_xlabel("")
    axes[0].legend().remove()
    axes[1].legend(title="Array size", frameon=False, ncols=3, loc="upper center")
    axes[0].text(0.01, 0.95, "(a)", transform=axes[0].transAxes, va="top", fontweight="bold")
    axes[1].text(0.01, 0.95, "(b)", transform=axes[1].transAxes, va="top", fontweight="bold")
    fig.savefig(COMBINED_FIGURE_PATH, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved figure: {COMBINED_FIGURE_PATH}")


def build_paper_peak_table(peak_table: pd.DataFrame) -> pd.DataFrame:
    """Format the refined peak table for direct paper use."""
    table = peak_table.copy()
    table["metric_label"] = table["metric"].map(METRIC_LABELS).fillna(table["metric"])

    preferred_columns = [
        "array_size",
        "metric",
        "metric_label",
        "peak_period",
        "peak_value",
        "boundary_peak_label",
        "lower_boundary_interval_label",
        "source_file",
    ]
    existing_columns = [column for column in preferred_columns if column in table.columns]
    paper_table = table[existing_columns].sort_values(["array_size", "metric"], ignore_index=True)
    paper_table = paper_table.rename(
        columns={
            "array_size": "N",
            "peak_period": "peak_period_s",
            "peak_value": "peak_value_unit_incident_amplitude",
        }
    )
    return paper_table


def save_paper_peak_table(peak_table: pd.DataFrame) -> None:
    """Write the paper-formatted refined centre peak table."""
    paper_table = build_paper_peak_table(peak_table)
    paper_table.to_csv(PAPER_PEAK_TABLE_PATH, index=False, float_format="%.12g")
    print(f"Saved table: {PAPER_PEAK_TABLE_PATH}")


def write_captions() -> None:
    """Write reusable figure and table captions for the refined paper outputs."""
    captions = f"""# Refined centre-response paper captions

## Figure: `{MEAN_FIGURE_PATH.name}`
Refined period-scan mean centre free-surface response for the fixed N=4, N=6,
and N=8 circular-cylinder ring arrays over T = {PERIOD_WINDOW_TEXT}. The plotted
quantity is the mean of the five predefined centre probes P0--P4, normalized by
unit incident-wave amplitude.

## Figure: `{MAX_FIGURE_PATH.name}`
Refined period-scan maximum centre free-surface response for the fixed N=4, N=6,
and N=8 circular-cylinder ring arrays over T = {PERIOD_WINDOW_TEXT}. The plotted
quantity is the maximum over the same five centre probes P0--P4, normalized by
unit incident-wave amplitude.

## Figure: `{COMBINED_FIGURE_PATH.name}`
Two-panel comparison of refined centre responses over T = {PERIOD_WINDOW_TEXT}:
(a) mean centre amplitude and (b) maximum centre amplitude for the fixed N=4,
N=6, and N=8 ring arrays. All curves use the same probe definitions and unit
incident-wave-amplitude normalization.

## Table: `{PAPER_PEAK_TABLE_PATH.name}`
Peak refined centre-response values extracted from the local refined scan CSVs
for the fixed N=4, N=6, and N=8 ring arrays over T = {PERIOD_WINDOW_TEXT}. The
reported peaks preserve the boundary-peak labels from the refined peak table and
do not assign physical resonance labels.
"""
    CAPTIONS_PATH.write_text(captions, encoding="utf-8")
    print(f"Saved captions: {CAPTIONS_PATH}")


def main() -> None:
    """Generate all refined paper-output assets from local refined CSVs."""
    ensure_output_directories()
    summaries = read_all_summaries()
    peak_table = read_peak_table()

    save_single_metric_figure(summaries, MEAN_SPEC)
    save_single_metric_figure(summaries, MAX_SPEC)
    save_combined_figure(summaries)
    save_paper_peak_table(peak_table)
    write_captions()


if __name__ == "__main__":
    main()
