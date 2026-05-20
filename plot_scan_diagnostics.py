"""Generate diagnostic tables and figures for completed N=4/N=6/N=8 scans.

This script is post-processing only: it reads existing CSV/Markdown files from
``outputs/`` and writes anomaly-check CSV plus diagnostic figures. It does not
import Capytaine, instantiate a BEM solver, or call solver.solve(...).
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FormatStrFormatter

OUTPUT_DIR = Path("outputs")
FIGURE_DIR = Path("figures")

PERIOD_MIN = 0.90
PERIOD_MAX = 2.00
PERIOD_TOLERANCE = 5e-6
ANOMALY_FALLBACK_INTERVAL = (0.90, 0.93)
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
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)


def _paths(array_size: int) -> dict[str, Path]:
    prefix = f"N{array_size}"
    return {
        "summary": OUTPUT_DIR / f"{prefix}_period_scan_summary_0p90_2p00.csv",
        "point": OUTPUT_DIR / f"{prefix}_period_scan_point_probes_0p90_2p00.csv",
        "report": OUTPUT_DIR / f"{prefix}_analysis_report.md",
        "recommend": OUTPUT_DIR / f"{prefix}_plot_recommendations.csv",
        "anomaly": OUTPUT_DIR / f"anomaly_check_{prefix}.csv",
        "fig_center_summary": FIGURE_DIR / f"{prefix}_center_summary_0p90_2p00",
        "fig_center_five": FIGURE_DIR / f"{prefix}_center_five_points_0p90_2p00",
        "fig_front_rear": FIGURE_DIR / f"{prefix}_front_rear_S_0p90_2p00",
    }


def require_columns(df: pd.DataFrame, required: Iterable[str], table_name: str) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"{table_name} is missing required columns: {missing}")


def _parse_intervals(report_text: str) -> list[tuple[float, float]]:
    interval_pattern = re.compile(r"(?<!\\d)(\\d+\\.\\d{2})\\s*[-–—]\\s*(\\d+\\.\\d{2})(?!\\d)")
    keyword_pattern = re.compile(r"anomal|异常|跳变", re.IGNORECASE)
    intervals: list[tuple[float, float]] = []
    for line in report_text.splitlines():
        if not keyword_pattern.search(line):
            continue
        for s, e in interval_pattern.findall(line):
            start, end = float(s), float(e)
            if start > end:
                start, end = end, start
            intervals.append((round(start, 2), round(end, 2)))
    return intervals or [ANOMALY_FALLBACK_INTERVAL]


def _period_in_intervals(period: float, intervals: Iterable[tuple[float, float]]) -> bool:
    return any(start - PERIOD_TOLERANCE <= period <= end + PERIOD_TOLERANCE for start, end in intervals)


def read_inputs(array_size: int) -> tuple[pd.DataFrame, pd.DataFrame, str, pd.DataFrame, dict[str, Path]]:
    paths = _paths(array_size)
    required_paths = [paths["summary"], paths["point"], paths["report"], paths["recommend"]]
    missing = [p for p in required_paths if not p.exists()]
    if missing:
        missing_text = "\n".join(f"- {p}" for p in missing)
        raise FileNotFoundError(
            f"Missing required N={array_size} post-processing input files. "
            "This script only reads existing outputs and does not generate raw scan CSV files:\n"
            f"{missing_text}"
        )

    summary_df = pd.read_csv(paths["summary"]).copy()
    point_df = pd.read_csv(paths["point"]).copy()
    report_text = paths["report"].read_text(encoding="utf-8")
    rec_df = pd.read_csv(paths["recommend"]).copy()

    require_columns(summary_df, SUMMARY_REQUIRED_COLUMNS, str(paths["summary"]))
    require_columns(point_df, POINT_REQUIRED_COLUMNS, str(paths["point"]))

    summary_df["period"] = pd.to_numeric(summary_df["period"], errors="coerce").round(2)
    point_df["period"] = pd.to_numeric(point_df["period"], errors="coerce").round(2)
    for c in SUMMARY_REQUIRED_COLUMNS:
        if c != "period":
            summary_df[c] = pd.to_numeric(summary_df[c], errors="coerce")
    point_df["total_abs"] = pd.to_numeric(point_df["total_abs"], errors="coerce")

    if summary_df[SUMMARY_REQUIRED_COLUMNS].isna().any().any():
        raise ValueError(f"{paths['summary']} contains NaN/non-numeric values in required columns")
    if point_df[POINT_REQUIRED_COLUMNS].isna().any().any():
        raise ValueError(f"{paths['point']} contains NaN/non-numeric values in required columns")

    return summary_df, point_df, report_text, rec_df, paths


def build_anomaly_check_table(summary_df: pd.DataFrame, point_df: pd.DataFrame, array_size: int, report_text: str) -> pd.DataFrame:
    center_point_df = point_df.loc[point_df["probe"].isin(CENTER_PROBES), ["period", "probe", "total_abs"]]
    if int(center_point_df.duplicated(["period", "probe"]).sum()) > 0:
        raise ValueError("Duplicate (period, probe) rows found in point probes")

    point_wide = center_point_df.pivot(index="period", columns="probe", values="total_abs")
    for p in CENTER_PROBES:
        if p not in point_wide.columns:
            raise ValueError(f"Missing center probe in point CSV: {p}")
    point_wide = point_wide[CENTER_PROBES].rename(columns={p: f"{p}_total_abs" for p in CENTER_PROBES})

    table = (
        summary_df[SUMMARY_REQUIRED_COLUMNS]
        .drop_duplicates("period")
        .merge(point_wide.reset_index(), on="period", how="left", validate="one_to_one")
        .sort_values("period")
        .reset_index(drop=True)
    )

    for col in [c for c in table.columns if c != "period"]:
        table[f"delta_{col}"] = table[col].diff()

    intervals = _parse_intervals(report_text)
    interval_text = "; ".join(f"{s:.2f}-{e:.2f} s" for s, e in intervals)
    table["note"] = [
        f"near analysis-report anomaly interval ({interval_text})" if _period_in_intervals(float(p), intervals) else ""
        for p in table["period"]
    ]

    return table[ANOMALY_OUTPUT_COLUMNS]


def _add_common_style(ax: plt.Axes) -> None:
    ax.set_xlim(PERIOD_MIN, PERIOD_MAX)
    ax.xaxis.set_major_formatter(FormatStrFormatter("%.2f"))
    ax.set_xlabel("Period (s)")
    ax.grid(True, linestyle="--", linewidth=0.7, alpha=0.35)


def _add_anomaly_interval(ax: plt.Axes, label: str = "Anomaly-check interval") -> None:
    ax.axvspan(ANOMALY_FALLBACK_INTERVAL[0], ANOMALY_FALLBACK_INTERVAL[1], color="tab:orange", alpha=0.16, label=label, zorder=0)


def _save_png_pdf(fig: plt.Figure, stem: Path) -> None:
    fig.savefig(stem.with_suffix(".png"), dpi=DPI, bbox_inches="tight")
    fig.savefig(stem.with_suffix(".pdf"), dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def plot_center_summary(summary_df: pd.DataFrame, array_size: int) -> None:
    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    _add_anomaly_interval(ax)
    ax.plot(summary_df["period"], summary_df["center_mean_abs"], label="center_mean_abs (total_abs)", linewidth=2.0)
    ax.plot(summary_df["period"], summary_df["center_max_abs"], label="center_max_abs (total_abs)", linewidth=2.0)

    idx_mean = summary_df["center_mean_abs"].idxmax()
    idx_max = summary_df["center_max_abs"].idxmax()
    for idx, metric, color in [(idx_mean, "center_mean_abs", "tab:blue"), (idx_max, "center_max_abs", "tab:green")]:
        x = float(summary_df.loc[idx, "period"])
        y = float(summary_df.loc[idx, metric])
        ax.scatter([x], [y], color=color, zorder=5)
        ax.annotate(f"Peak {metric}: T={x:.2f} s", xy=(x, y), xytext=(8, 8), textcoords="offset points", fontsize=8)

    ax.set_ylabel("Normalized free-surface amplitude")
    ax.set_title(f"N={array_size} center-response indicators over 0.90–2.00 s")
    _add_common_style(ax)
    ax.legend(loc="best")
    _save_png_pdf(fig, _paths(array_size)["fig_center_summary"])


def plot_center_five_points(point_df: pd.DataFrame, array_size: int) -> None:
    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    _add_anomaly_interval(ax)
    for probe in CENTER_PROBES:
        probe_df = point_df.loc[point_df["probe"] == probe].sort_values("period")
        ax.plot(probe_df["period"], probe_df["total_abs"], linewidth=1.8, label=f"{probe} total_abs")
    ax.set_ylabel("Normalized free-surface amplitude")
    ax.set_title(f"N={array_size} five central probes over 0.90–2.00 s")
    _add_common_style(ax)
    ax.legend(loc="best", ncol=2)
    _save_png_pdf(fig, _paths(array_size)["fig_center_five"])


def plot_front_rear_S(summary_df: pd.DataFrame, array_size: int) -> None:
    fig, ax1 = plt.subplots(figsize=(8.8, 5.0))
    _add_anomaly_interval(ax1)
    l1, = ax1.plot(summary_df["period"], summary_df["front_abs"], linewidth=2.0, label="front_abs (total_abs)")
    l2, = ax1.plot(summary_df["period"], summary_df["rear_abs"], linewidth=2.0, label="rear_abs (total_abs)")
    ax1.set_ylabel("Normalized probe amplitude")

    ax2 = ax1.twinx()
    l3, = ax2.plot(summary_df["period"], summary_df["S_rear_front"], color="tab:red", linewidth=2.0, label="S_rear_front")
    ax2.set_ylabel("S_rear_front (-), transmission-like indicator")

    idx_rear = summary_df["rear_abs"].idxmax()
    xr, yr = float(summary_df.loc[idx_rear, "period"]), float(summary_df.loc[idx_rear, "rear_abs"])
    ax1.scatter([xr], [yr], color="tab:orange", zorder=6)
    ax1.annotate(f"Peak rear_abs: T={xr:.2f} s", xy=(xr, yr), xytext=(8, 8), textcoords="offset points", fontsize=8)

    idx_s = summary_df["S_rear_front"].idxmax()
    xs, ys = float(summary_df.loc[idx_s, "period"]), float(summary_df.loc[idx_s, "S_rear_front"])
    ax2.scatter([xs], [ys], color="tab:red", zorder=6)
    ax2.annotate(f"Peak S_rear_front: T={xs:.2f} s", xy=(xs, ys), xytext=(8, -14), textcoords="offset points", fontsize=8)

    ax1.set_title(f"N={array_size} front/rear amplitudes and transmission-like indicator")
    _add_common_style(ax1)
    lines = [l1, l2, l3]
    labels = [ln.get_label() for ln in lines]
    ax1.legend(lines, labels, loc="best")
    _save_png_pdf(fig, _paths(array_size)["fig_front_rear"])


def main() -> None:
    parser = argparse.ArgumentParser(description="General diagnostic plotting for completed N=4/N=6/N=8 scans")
    parser.add_argument("--array-size", type=int, choices=[4, 6, 8], required=True)
    args = parser.parse_args()

    ensure_dirs()
    summary_df, point_df, report_text, _rec_df, paths = read_inputs(args.array_size)
    anomaly_df = build_anomaly_check_table(summary_df, point_df, args.array_size, report_text)

    if report_text:
        _ = report_text  # Explicitly retained as required input context.

    anomaly_df.to_csv(paths["anomaly"], index=False)
    plot_center_summary(summary_df, args.array_size)
    plot_center_five_points(point_df, args.array_size)
    plot_front_rear_S(summary_df, args.array_size)

    print(f"Saved anomaly table: {paths['anomaly']}")
    print(f"Saved figures: {paths['fig_center_summary'].with_suffix('.png')}, {paths['fig_center_five'].with_suffix('.png')}, {paths['fig_front_rear'].with_suffix('.png')}")


if __name__ == "__main__":
    main()
