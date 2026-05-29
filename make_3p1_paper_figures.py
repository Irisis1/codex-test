"""Generate paper-ready Section 3.1 central-response sweep figures.

This script is post-processing only: it reads existing CSV outputs, redraws the
main-scan and refined two-panel central-response figures, and writes updated
caption text. It does not run Capytaine, alter physical parameters, or modify
any source CSV files.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import pandas as pd

ARRAY_SIZES = (4, 6, 8)
OUTPUT_DIR = Path("outputs")
FIGURE_DIR = Path("figures")

MAIN_PERIOD_MIN = 0.90
MAIN_PERIOD_MAX = 2.00
REFINED_PERIOD_MIN = 0.85
REFINED_PERIOD_MAX = 1.05
NEAR_BOUNDARY_MIN = 0.90
NEAR_BOUNDARY_MAX = 0.93

MAIN_COMBINED_CSV = OUTPUT_DIR / "N468_key_metrics_comparison.csv"
MAIN_SUMMARY_CSVS = {
    n: OUTPUT_DIR / f"N{n}_period_scan_summary_0p90_2p00.csv" for n in ARRAY_SIZES
}
REFINED_SUMMARY_CSVS = {
    n: OUTPUT_DIR / f"N{n}_refined_period_scan_summary_0p85_1p05.csv"
    for n in ARRAY_SIZES
}

MAIN_FIGURE_PATH = FIGURE_DIR / "N468_main_center_response_0p90_2p00_paper_combined.png"
REFINED_FIGURE_PATH = FIGURE_DIR / "N468_refined_center_response_0p85_1p05_paper_combined.png"
CAPTIONS_PATH = OUTPUT_DIR / "N468_3p1_figure_captions_updated.md"

REQUIRED_COLUMNS = {"period", "array_size", "center_mean_abs", "center_max_abs"}
PLOT_STYLES = {
    4: {"marker": "o", "linestyle": "-"},
    6: {"marker": "s", "linestyle": "--"},
    8: {"marker": "^", "linestyle": "-."},
}


@dataclass(frozen=True)
class ScanSpec:
    """Metadata for one central-response scan figure."""

    figure_path: Path
    period_min: float
    period_max: float
    panel_title_prefix: str
    show_near_boundary_interval: bool


MAIN_SCAN = ScanSpec(
    figure_path=MAIN_FIGURE_PATH,
    period_min=MAIN_PERIOD_MIN,
    period_max=MAIN_PERIOD_MAX,
    panel_title_prefix="Main-scan",
    show_near_boundary_interval=True,
)
REFINED_SCAN = ScanSpec(
    figure_path=REFINED_FIGURE_PATH,
    period_min=REFINED_PERIOD_MIN,
    period_max=REFINED_PERIOD_MAX,
    panel_title_prefix="Refined short-period",
    show_near_boundary_interval=False,
)


def ensure_output_directories() -> None:
    """Create output directories for derived paper assets."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)


def require_columns(dataframe: pd.DataFrame, path: Path) -> None:
    """Validate the columns needed for central-response plotting."""
    missing = sorted(REQUIRED_COLUMNS - set(dataframe.columns))
    if missing:
        raise ValueError(f"{path} is missing required columns: {missing}")


def normalize_summary(dataframe: pd.DataFrame, path: Path, expected_array_size: int | None) -> pd.DataFrame:
    """Return a validated numeric summary table without changing source CSV files."""
    summary = dataframe.copy()
    if expected_array_size is not None and "array_size" not in summary.columns:
        summary["array_size"] = expected_array_size

    require_columns(summary, path)
    summary["period"] = pd.to_numeric(summary["period"], errors="raise")
    summary["array_size"] = pd.to_numeric(summary["array_size"], errors="raise").astype(int)
    summary["center_mean_abs"] = pd.to_numeric(summary["center_mean_abs"], errors="raise")
    summary["center_max_abs"] = pd.to_numeric(summary["center_max_abs"], errors="raise")

    if expected_array_size is not None:
        unexpected = sorted(set(summary["array_size"]) - {expected_array_size})
        if unexpected:
            raise ValueError(
                f"{path} contains array_size values that do not match N={expected_array_size}: "
                f"{unexpected}"
            )

    return summary.sort_values(["array_size", "period"], ignore_index=True)


def read_per_array_summaries(paths_by_n: dict[int, Path]) -> dict[int, pd.DataFrame]:
    """Read one summary CSV for each array size."""
    missing = [str(path) for path in paths_by_n.values() if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing required per-array summary CSV files:\n" + "\n".join(missing))

    return {
        n: normalize_summary(pd.read_csv(path), path, expected_array_size=n)
        for n, path in paths_by_n.items()
    }


def read_main_summaries() -> dict[int, pd.DataFrame]:
    """Read main-scan central-response data from the preferred available CSVs."""
    if MAIN_COMBINED_CSV.exists():
        combined = normalize_summary(
            pd.read_csv(MAIN_COMBINED_CSV), MAIN_COMBINED_CSV, expected_array_size=None
        )
        summaries: dict[int, pd.DataFrame] = {}
        for n in ARRAY_SIZES:
            current = combined[combined["array_size"] == n].copy()
            if current.empty:
                raise ValueError(f"{MAIN_COMBINED_CSV} contains no rows for N={n}")
            summaries[n] = current.sort_values("period", ignore_index=True)
        return summaries

    return read_per_array_summaries(MAIN_SUMMARY_CSVS)


def read_refined_summaries() -> dict[int, pd.DataFrame]:
    """Read refined short-period central-response data."""
    return read_per_array_summaries(REFINED_SUMMARY_CSVS)


def check_period_coverage(
    summaries: dict[int, pd.DataFrame], period_min: float, period_max: float, label: str
) -> None:
    """Ensure all curves include the requested plotting interval."""
    for n, summary in summaries.items():
        min_available = float(summary["period"].min())
        max_available = float(summary["period"].max())
        if min_available > period_min or max_available < period_max:
            raise ValueError(
                f"N={n} {label} data cover T={min_available:.3f}--{max_available:.3f} s, "
                f"not the requested T={period_min:.3f}--{period_max:.3f} s"
            )


def filter_period_window(
    summaries: dict[int, pd.DataFrame], period_min: float, period_max: float
) -> dict[int, pd.DataFrame]:
    """Select the requested period window for plotting."""
    filtered = {}
    for n, summary in summaries.items():
        in_window = summary["period"].between(period_min, period_max, inclusive="both")
        filtered[n] = summary.loc[in_window].sort_values("period", ignore_index=True)
    return filtered


def add_curves(ax: plt.Axes, summaries: dict[int, pd.DataFrame], column: str) -> None:
    """Plot central-response curves for N=4, N=6, and N=8."""
    for n in ARRAY_SIZES:
        summary = summaries[n]
        style = PLOT_STYLES[n]
        ax.plot(
            summary["period"],
            summary[column],
            label=f"N={n}",
            linewidth=1.7,
            markersize=3.2,
            markevery=max(1, len(summary) // 16),
            marker=style["marker"],
            linestyle=style["linestyle"],
        )


def add_near_boundary_interval(ax: plt.Axes) -> None:
    """Mark the main-scan lower-boundary inspection interval."""
    ax.axvspan(
        NEAR_BOUNDARY_MIN,
        NEAR_BOUNDARY_MAX,
        color="0.75",
        alpha=0.35,
        linewidth=0.0,
        label="Near-boundary inspection interval",
    )


def save_combined_figure(summaries: dict[int, pd.DataFrame], spec: ScanSpec) -> None:
    """Save a two-panel central-response figure at paper-ready resolution."""
    check_period_coverage(summaries, spec.period_min, spec.period_max, spec.panel_title_prefix)
    plot_data = filter_period_window(summaries, spec.period_min, spec.period_max)

    fig, axes = plt.subplots(2, 1, figsize=(7.2, 7.2), sharex=True, constrained_layout=True)

    add_curves(axes[0], plot_data, "center_mean_abs")
    add_curves(axes[1], plot_data, "center_max_abs")

    if spec.show_near_boundary_interval:
        add_near_boundary_interval(axes[0])
        add_near_boundary_interval(axes[1])

    axes[0].set_title(r"(a) Mean central response, $A_{c,\mathrm{mean}}$")
    axes[1].set_title(r"(b) Maximum central response, $A_{c,\max}$")
    axes[0].set_ylabel(r"Mean central response, $A_{c,\mathrm{mean}}$")
    axes[1].set_ylabel(r"Maximum central response, $A_{c,\max}$")
    axes[1].set_xlabel(r"Wave period, $T$ (s)")

    for ax in axes:
        ax.set_xlim(spec.period_min, spec.period_max)
        ax.grid(True, alpha=0.30, linewidth=0.7)

    handles, labels = axes[0].get_legend_handles_labels()
    unique_handles: list[object] = []
    unique_labels: list[str] = []
    for handle, label in zip(handles, labels):
        if label not in unique_labels:
            unique_handles.append(handle)
            unique_labels.append(label)
    axes[0].legend(unique_handles, unique_labels, frameon=False, ncols=2, loc="best")
    axes[1].legend().remove()

    fig.savefig(spec.figure_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Generated: {spec.figure_path}")


def write_captions() -> None:
    """Write the updated Section 3.1 figure caption draft."""
    captions = """# Updated Section 3.1 figure caption drafts

Figure X. Main-scan central responses of the fixed circular-cylinder ring arrays with N = 4, 6, and 8 over T = 0.90–2.00 s with ΔT = 0.01 s: (a) mean central response A_c,mean and (b) maximum central response A_c,max. Both quantities were evaluated from the five central probes and are expressed as incident-amplitude-normalized frequency-domain complex-amplitude magnitudes. Peaks located near the lower scan boundary are treated cautiously because shorter periods are not resolved in the main scan.

Figure Y. Refined short-period central responses of the fixed circular-cylinder ring arrays with N = 4, 6, and 8 over T = 0.85–1.05 s with ΔT = 0.005 s: (a) mean central response A_c,mean and (b) maximum central response A_c,max. The refined scan was used to identify short-period peak locations near the lower boundary of the main scan. All amplitudes are incident-amplitude-normalized frequency-domain complex-amplitude magnitudes.
"""
    CAPTIONS_PATH.write_text(captions, encoding="utf-8")
    print(f"Generated: {CAPTIONS_PATH}")


def report_expected_outputs(paths: Iterable[Path]) -> None:
    """Print final output paths requested by the Section 3.1 plotting workflow."""
    print("Output paths:")
    for path in paths:
        print(path)


def main() -> None:
    """Generate Section 3.1 paper figures and caption drafts from CSV files."""
    ensure_output_directories()
    write_captions()

    main_summaries = read_main_summaries()
    save_combined_figure(main_summaries, MAIN_SCAN)

    refined_summaries = read_refined_summaries()
    save_combined_figure(refined_summaries, REFINED_SCAN)

    report_expected_outputs([MAIN_FIGURE_PATH, REFINED_FIGURE_PATH, CAPTIONS_PATH])


if __name__ == "__main__":
    main()
