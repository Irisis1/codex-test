"""Generate diagnostic tables and figures for the completed N=8 scan.

This script is intentionally a post-processing-only workflow. It reads the
existing N=8 CSV/report files from ``outputs/`` and writes one anomaly-check CSV
plus diagnostic figures. It does not import Capytaine, instantiate a BEM solver,
or call the BEM solve method.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FormatStrFormatter

OUTPUT_DIR = Path("outputs")
FIGURE_DIR = Path("figures")

SUMMARY_CSV = OUTPUT_DIR / "N8_period_scan_summary_0p90_2p00.csv"
POINT_CSV = OUTPUT_DIR / "N8_period_scan_point_probes_0p90_2p00.csv"
REPORT_MD = OUTPUT_DIR / "N8_analysis_report.md"
PLOT_RECOMMENDATIONS_CSV = OUTPUT_DIR / "N8_plot_recommendations.csv"

ANOMALY_CHECK_CSV = OUTPUT_DIR / "anomaly_check_N8.csv"
CENTER_SUMMARY_FIG = FIGURE_DIR / "N8_center_summary_0p90_2p00"
CENTER_FIVE_POINTS_FIG = FIGURE_DIR / "N8_center_five_points_0p90_2p00"
FRONT_REAR_S_FIG = FIGURE_DIR / "N8_front_rear_S_0p90_2p00"

PERIOD_MIN = 0.90
PERIOD_MAX = 2.00
ANOMALY_FALLBACK_INTERVAL = (0.90, 0.93)
PERIOD_TOLERANCE = 5e-6
DPI = 300

CENTER_PROBES = ["P0", "P1", "P2", "P3", "P4"]
SUMMARY_REQUIRED_COLUMNS = [
    "period",
    "center_mean_abs",
    "center_max_abs",
    "front_abs",
    "rear_abs",
    "S_rear_front",
]
POINT_REQUIRED_COLUMNS = ["period", "probe", "total_abs"]
ANOMALY_OUTPUT_COLUMNS = [
    "period",
    "center_mean_abs",
    "center_max_abs",
    "front_abs",
    "rear_abs",
    "S_rear_front",
    "P0_total_abs",
    "P1_total_abs",
    "P2_total_abs",
    "P3_total_abs",
    "P4_total_abs",
    "delta_center_mean_abs",
    "delta_center_max_abs",
    "delta_front_abs",
    "delta_rear_abs",
    "delta_S_rear_front",
    "delta_P0_total_abs",
    "delta_P1_total_abs",
    "delta_P2_total_abs",
    "delta_P3_total_abs",
    "delta_P4_total_abs",
    "note",
]


def ensure_dirs() -> None:
    """Create output directories for generated diagnostics."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)


def require_columns(dataframe: pd.DataFrame, required_columns: Iterable[str], table_name: str) -> None:
    """Raise a clear error if required columns are missing."""
    missing = [column for column in required_columns if column not in dataframe.columns]
    if missing:
        raise ValueError(f"{table_name} is missing required columns: {missing}")


def read_inputs() -> tuple[pd.DataFrame, pd.DataFrame, str, pd.DataFrame]:
    """Read required N=8 post-processing inputs and validate core columns."""
    required_paths = [SUMMARY_CSV, POINT_CSV, REPORT_MD, PLOT_RECOMMENDATIONS_CSV]
    missing = [path for path in required_paths if not path.exists()]
    if missing:
        missing_text = "\n".join(f"- {path}" for path in missing)
        raise FileNotFoundError(
            "Missing required N=8 diagnostic input files. This script only reads "
            "existing post-processing outputs and will not regenerate raw scan CSVs:\n"
            f"{missing_text}"
        )

    summary_df = pd.read_csv(SUMMARY_CSV)
    point_df = pd.read_csv(POINT_CSV)
    report_text = REPORT_MD.read_text(encoding="utf-8")
    recommendation_df = pd.read_csv(PLOT_RECOMMENDATIONS_CSV)

    require_columns(summary_df, SUMMARY_REQUIRED_COLUMNS, str(SUMMARY_CSV))
    require_columns(point_df, POINT_REQUIRED_COLUMNS, str(POINT_CSV))

    summary_df = summary_df.copy()
    point_df = point_df.copy()
    summary_df["period"] = pd.to_numeric(summary_df["period"], errors="coerce").round(2)
    point_df["period"] = pd.to_numeric(point_df["period"], errors="coerce").round(2)

    numeric_summary_columns = [column for column in SUMMARY_REQUIRED_COLUMNS if column != "period"]
    for column in numeric_summary_columns:
        summary_df[column] = pd.to_numeric(summary_df[column], errors="coerce")
    point_df["total_abs"] = pd.to_numeric(point_df["total_abs"], errors="coerce")

    if summary_df[SUMMARY_REQUIRED_COLUMNS].isna().any().any():
        raise ValueError(f"{SUMMARY_CSV} contains non-numeric or NaN values in required columns.")
    if point_df[POINT_REQUIRED_COLUMNS].isna().any().any():
        raise ValueError(f"{POINT_CSV} contains non-numeric or NaN values in required columns.")

    missing_center_probes = sorted(set(CENTER_PROBES) - set(point_df["probe"].astype(str)))
    if missing_center_probes:
        raise ValueError(f"{POINT_CSV} is missing center probes: {missing_center_probes}")

    return summary_df, point_df, report_text, recommendation_df


def parse_anomaly_intervals(report_text: str) -> list[tuple[float, float]]:
    """Extract anomaly intervals from report lines mentioning anomalies.

    The fallback interval is the user-requested N=8 anomaly-check band. The
    output table still covers all available periods, not only this band.
    """
    intervals: list[tuple[float, float]] = []
    interval_pattern = re.compile(r"(?<!\d)(\d+\.\d{2})\s*[-–—]\s*(\d+\.\d{2})(?!\d)")
    keyword_pattern = re.compile(r"anomal|异常|跳变", re.IGNORECASE)
    for line in report_text.splitlines():
        if not keyword_pattern.search(line):
            continue
        for start_text, end_text in interval_pattern.findall(line):
            start, end = float(start_text), float(end_text)
            if start > end:
                start, end = end, start
            intervals.append((round(start, 2), round(end, 2)))

    if not intervals:
        intervals.append(ANOMALY_FALLBACK_INTERVAL)

    unique_intervals: list[tuple[float, float]] = []
    for interval in intervals:
        if interval not in unique_intervals:
            unique_intervals.append(interval)
    return unique_intervals


def period_in_intervals(period: float, intervals: Iterable[tuple[float, float]]) -> bool:
    """Return True if a period is inside any anomaly-check interval."""
    return any(start - PERIOD_TOLERANCE <= period <= end + PERIOD_TOLERANCE for start, end in intervals)


def build_anomaly_check_table(summary_df: pd.DataFrame, point_df: pd.DataFrame) -> pd.DataFrame:
    """Build a period-by-period anomaly-check table from total_abs responses."""
    require_columns(summary_df, SUMMARY_REQUIRED_COLUMNS, "summary_df")
    require_columns(point_df, POINT_REQUIRED_COLUMNS, "point_df")

    center_point_df = point_df.loc[point_df["probe"].isin(CENTER_PROBES), ["period", "probe", "total_abs"]]
    duplicate_count = int(center_point_df.duplicated(["period", "probe"]).sum())
    if duplicate_count:
        raise ValueError(f"Point-probe table has duplicate period/probe rows: {duplicate_count}")

    point_wide = center_point_df.pivot(index="period", columns="probe", values="total_abs")
    missing_columns = [probe for probe in CENTER_PROBES if probe not in point_wide.columns]
    if missing_columns:
        raise ValueError(f"Point-probe table is missing total_abs columns for: {missing_columns}")
    point_wide = point_wide[CENTER_PROBES].rename(columns={probe: f"{probe}_total_abs" for probe in CENTER_PROBES})

    table = (
        summary_df[SUMMARY_REQUIRED_COLUMNS]
        .drop_duplicates("period")
        .merge(point_wide.reset_index(), on="period", how="left", validate="one_to_one")
        .sort_values("period")
        .reset_index(drop=True)
    )
    p_columns = [f"{probe}_total_abs" for probe in CENTER_PROBES]
    if table[p_columns].isna().any().any():
        missing_periods = table.loc[table[p_columns].isna().any(axis=1), "period"].map(lambda value: f"{value:.2f}")
        raise ValueError("Missing center-probe total_abs rows for periods: " + ", ".join(missing_periods))

    metric_columns = [column for column in table.columns if column != "period"]
    for column in metric_columns:
        table[f"delta_{column}"] = table[column].diff()

    report_text = REPORT_MD.read_text(encoding="utf-8") if REPORT_MD.exists() else ""
    intervals = parse_anomaly_intervals(report_text)
    interval_text = "; ".join(f"{start:.2f}-{end:.2f} s" for start, end in intervals)
    table["note"] = [
        f"near analysis-report anomaly interval ({interval_text})" if period_in_intervals(float(period), intervals) else ""
        for period in table["period"]
    ]

    table = table[ANOMALY_OUTPUT_COLUMNS]
    table["period"] = table["period"].round(2)
    return table


def add_anomaly_interval(ax: plt.Axes) -> None:
    """Add the common anomaly-check interval marker to an axes."""
    ax.axvspan(
        ANOMALY_FALLBACK_INTERVAL[0],
        ANOMALY_FALLBACK_INTERVAL[1],
        color="tab:orange",
        alpha=0.16,
        label="Anomaly-check interval",
        zorder=0,
    )


def format_period_axis(ax: plt.Axes) -> None:
    """Apply common period-axis formatting."""
    ax.set_xlim(PERIOD_MIN, PERIOD_MAX)
    ax.xaxis.set_major_formatter(FormatStrFormatter("%.2f"))
    ax.grid(True, alpha=0.28, linewidth=0.7)


def save_figure(fig: plt.Figure, stem: Path) -> None:
    """Save matching PNG and PDF versions of a diagnostic figure."""
    fig.savefig(stem.with_suffix(".png"), dpi=DPI, bbox_inches="tight")
    fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)


def peak_row(dataframe: pd.DataFrame, column: str) -> pd.Series:
    """Return the row where a metric has its global maximum."""
    return dataframe.loc[dataframe[column].idxmax()]


def plot_center_summary(summary_df: pd.DataFrame) -> None:
    """Plot center_mean_abs and center_max_abs over the N=8 scan."""
    require_columns(summary_df, ["period", "center_mean_abs", "center_max_abs"], "summary_df")
    data = summary_df.sort_values("period")
    mean_peak = peak_row(data, "center_mean_abs")
    max_peak = peak_row(data, "center_max_abs")

    fig, ax = plt.subplots(figsize=(7.0, 4.5), constrained_layout=True)
    add_anomaly_interval(ax)
    ax.plot(data["period"], data["center_mean_abs"], color="tab:blue", linewidth=1.8, label="Center mean")
    ax.plot(data["period"], data["center_max_abs"], color="tab:red", linewidth=1.8, label="Center max")
    ax.scatter(mean_peak["period"], mean_peak["center_mean_abs"], color="tab:blue", edgecolor="black", zorder=4, label="Mean peak")
    ax.scatter(max_peak["period"], max_peak["center_max_abs"], color="tab:red", edgecolor="black", zorder=4, marker="s", label="Max peak")

    ax.annotate(
        f"mean peak: T={mean_peak['period']:.2f} s, value={mean_peak['center_mean_abs']:.3f}",
        xy=(mean_peak["period"], mean_peak["center_mean_abs"]),
        xytext=(12, 16),
        textcoords="offset points",
        arrowprops={"arrowstyle": "->", "color": "tab:blue", "lw": 0.9},
        fontsize=8.5,
        color="tab:blue",
    )
    ax.annotate(
        f"max peak: T={max_peak['period']:.2f} s, value={max_peak['center_max_abs']:.3f}",
        xy=(max_peak["period"], max_peak["center_max_abs"]),
        xytext=(12, -24),
        textcoords="offset points",
        arrowprops={"arrowstyle": "->", "color": "tab:red", "lw": 0.9},
        fontsize=8.5,
        color="tab:red",
    )

    ax.set_title("N=8 center-response indicators over 0.90–2.00 s")
    ax.set_xlabel("period (s)")
    ax.set_ylabel("Normalized free-surface amplitude")
    format_period_axis(ax)
    ax.legend(loc="best", fontsize=8.5)
    save_figure(fig, CENTER_SUMMARY_FIG)


def plot_center_five_points(point_df: pd.DataFrame) -> None:
    """Plot total_abs at the five central probes P0-P4."""
    require_columns(point_df, POINT_REQUIRED_COLUMNS, "point_df")
    center_point_df = point_df.loc[point_df["probe"].isin(CENTER_PROBES), ["period", "probe", "total_abs"]]
    point_wide = center_point_df.pivot(index="period", columns="probe", values="total_abs").sort_index()
    missing_columns = [probe for probe in CENTER_PROBES if probe not in point_wide.columns]
    if missing_columns:
        raise ValueError(f"Point-probe table is missing total_abs data for: {missing_columns}")

    fig, ax = plt.subplots(figsize=(7.0, 4.5), constrained_layout=True)
    add_anomaly_interval(ax)
    colors = ["tab:blue", "tab:orange", "tab:green", "tab:red", "tab:purple"]
    for probe, color in zip(CENTER_PROBES, colors):
        ax.plot(point_wide.index, point_wide[probe], linewidth=1.6, color=color, label=probe)

    ax.set_title("N=8 five central probes over 0.90–2.00 s")
    ax.set_xlabel("period (s)")
    ax.set_ylabel("Normalized free-surface amplitude")
    format_period_axis(ax)
    ax.legend(loc="best", fontsize=8.5)
    save_figure(fig, CENTER_FIVE_POINTS_FIG)


def plot_front_rear_S(summary_df: pd.DataFrame) -> None:
    """Plot front/rear amplitudes with S_rear_front as a transmission-like indicator."""
    require_columns(summary_df, ["period", "front_abs", "rear_abs", "S_rear_front"], "summary_df")
    data = summary_df.sort_values("period")
    rear_peak = peak_row(data, "rear_abs")
    s_peak = peak_row(data, "S_rear_front")
    same_peak_period = np.isclose(rear_peak["period"], s_peak["period"], atol=PERIOD_TOLERANCE)

    fig, ax_left = plt.subplots(figsize=(7.5, 4.8), constrained_layout=True)
    add_anomaly_interval(ax_left)
    front_line, = ax_left.plot(data["period"], data["front_abs"], color="tab:blue", linewidth=1.8, label="front_abs")
    rear_line, = ax_left.plot(data["period"], data["rear_abs"], color="tab:green", linewidth=1.8, label="rear_abs")
    rear_peak_marker = ax_left.scatter(
        rear_peak["period"],
        rear_peak["rear_abs"],
        color="tab:green",
        edgecolor="black",
        marker="s",
        zorder=5,
        label="rear_abs peak",
    )

    ax_right = ax_left.twinx()
    s_line, = ax_right.plot(
        data["period"],
        data["S_rear_front"],
        color="tab:red",
        linestyle="--",
        linewidth=1.8,
        label="S_rear_front, transmission-like indicator",
    )
    s_peak_marker = ax_right.scatter(
        s_peak["period"],
        s_peak["S_rear_front"],
        color="tab:red",
        edgecolor="black",
        marker="^",
        zorder=5,
        label="S_rear_front peak",
    )

    ax_left.annotate(
        f"rear peak: T={rear_peak['period']:.2f} s, value={rear_peak['rear_abs']:.3f}",
        xy=(rear_peak["period"], rear_peak["rear_abs"]),
        xytext=(10, 16),
        textcoords="offset points",
        arrowprops={"arrowstyle": "->", "color": "tab:green", "lw": 0.9},
        fontsize=8.5,
        color="tab:green",
    )
    same_period_text = " (same period as rear peak)" if same_peak_period else ""
    ax_right.annotate(
        f"S peak: T={s_peak['period']:.2f} s, value={s_peak['S_rear_front']:.3f}{same_period_text}",
        xy=(s_peak["period"], s_peak["S_rear_front"]),
        xytext=(10, -28),
        textcoords="offset points",
        arrowprops={"arrowstyle": "->", "color": "tab:red", "lw": 0.9},
        fontsize=8.5,
        color="tab:red",
    )

    ax_left.set_title("N=8 front/rear amplitudes and transmission-like indicator")
    ax_left.set_xlabel("period (s)")
    ax_left.set_ylabel("Normalized probe amplitude")
    ax_right.set_ylabel("S_rear_front (-), transmission-like indicator")
    format_period_axis(ax_left)

    handles = [front_line, rear_line, s_line, rear_peak_marker, s_peak_marker]
    labels = [handle.get_label() for handle in handles]
    ax_left.legend(handles, labels, loc="best", fontsize=8.3)
    save_figure(fig, FRONT_REAR_S_FIG)


def main() -> None:
    """Run the N=8 diagnostic plotting workflow."""
    ensure_dirs()
    summary_df, point_df, _report_text, _recommendation_df = read_inputs()
    anomaly_table = build_anomaly_check_table(summary_df, point_df)
    anomaly_table_for_csv = anomaly_table.copy()
    anomaly_table_for_csv["period"] = anomaly_table_for_csv["period"].map(lambda value: f"{value:.2f}")
    anomaly_table_for_csv.to_csv(ANOMALY_CHECK_CSV, index=False, float_format="%.10g")
    plot_center_summary(summary_df)
    plot_center_five_points(point_df)
    plot_front_rear_S(summary_df)
    print(f"Wrote anomaly check table: {ANOMALY_CHECK_CSV}")
    print(f"Wrote figures: {CENTER_SUMMARY_FIG.with_suffix('.png')}, {CENTER_FIVE_POINTS_FIG.with_suffix('.png')}, {FRONT_REAR_S_FIG.with_suffix('.png')}")


if __name__ == "__main__":
    main()
