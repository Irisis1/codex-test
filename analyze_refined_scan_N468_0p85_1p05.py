"""Validate and plot the N=4/6/8 refined 0.85--1.05 s scan CSV files.

This post-processing script reads only refined CSV files, prints the required
completeness checks, writes a compact centre-peak table, and generates three
figures.  It does not run Capytaine and does not edit the broader 0.90--2.00 s
scan outputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

ARRAY_SIZES = (4, 6, 8)
OUTPUT_DIR = Path("outputs")
FIGURE_DIR = Path("figures")
EXPECTED_PERIODS = np.array([round(ms / 1000.0, 3) for ms in range(850, 1055, 5)])
EXPECTED_PROBES = {"P0", "P1", "P2", "P3", "P4", "front", "rear"}
CENTER_PROBES = ["P0", "P1", "P2", "P3", "P4"]
TOLERANCE = 1e-9


@dataclass
class CheckResult:
    array_size: int
    check: str
    status: str
    detail: str


def refined_paths(array_size: int) -> dict[str, Path]:
    """Return refined input paths for one array size."""
    return {
        "summary": OUTPUT_DIR
        / f"N{array_size}_refined_period_scan_summary_0p85_1p05.csv",
        "point": OUTPUT_DIR
        / f"N{array_size}_refined_period_scan_point_probes_0p85_1p05.csv",
    }


def pass_fail(condition: bool) -> str:
    return "PASS" if condition else "FAIL"


def add_check(results: list[CheckResult], array_size: int, check: str, condition: bool, detail: str) -> None:
    results.append(CheckResult(array_size, check, pass_fail(condition), detail))


def read_refined_inputs(array_size: int) -> tuple[pd.DataFrame | None, pd.DataFrame | None, list[CheckResult]]:
    """Read input CSVs for one N and return existence checks."""
    paths = refined_paths(array_size)
    results: list[CheckResult] = []
    summary_exists = paths["summary"].exists()
    point_exists = paths["point"].exists()
    add_check(results, array_size, "summary exists", summary_exists, str(paths["summary"]))
    add_check(results, array_size, "point_probes exists", point_exists, str(paths["point"]))

    if not (summary_exists and point_exists):
        return None, None, results

    summary_df = pd.read_csv(paths["summary"])
    point_df = pd.read_csv(paths["point"])
    for dataframe in (summary_df, point_df):
        if "period" in dataframe.columns:
            dataframe["period"] = pd.to_numeric(dataframe["period"], errors="coerce").round(3)
    return summary_df, point_df, results


def periods_have_no_gaps_or_duplicates(summary_df: pd.DataFrame) -> tuple[bool, str]:
    periods = pd.to_numeric(summary_df.get("period", pd.Series(dtype=float)), errors="coerce")
    unique_periods = np.sort(periods.dropna().unique())
    missing = sorted(set(EXPECTED_PERIODS) - set(np.round(unique_periods, 3)))
    extra = sorted(set(np.round(unique_periods, 3)) - set(EXPECTED_PERIODS))
    duplicate_count = int(periods.duplicated().sum())
    ok = not missing and not extra and duplicate_count == 0
    detail = f"missing={missing}, extra={extra}, duplicate_summary_periods={duplicate_count}"
    return ok, detail


def validate_array(array_size: int, summary_df: pd.DataFrame, point_df: pd.DataFrame) -> list[CheckResult]:
    """Run required integrity checks for one array size."""
    results: list[CheckResult] = []

    period_values = pd.to_numeric(summary_df.get("period", pd.Series(dtype=float)), errors="coerce")
    unique_periods = np.sort(period_values.dropna().unique())
    add_check(
        results,
        array_size,
        "41 periods",
        len(unique_periods) == 41,
        f"actual_unique_summary_periods={len(unique_periods)}, expected=41",
    )
    min_ok = len(period_values.dropna()) > 0 and np.isclose(period_values.min(), 0.85, atol=TOLERANCE)
    max_ok = len(period_values.dropna()) > 0 and np.isclose(period_values.max(), 1.05, atol=TOLERANCE)
    add_check(
        results,
        array_size,
        "period min/max 0.85/1.05",
        min_ok and max_ok,
        f"min={period_values.min() if len(period_values.dropna()) else 'NA'}, max={period_values.max() if len(period_values.dropna()) else 'NA'}",
    )
    no_gap_duplicate_ok, gap_detail = periods_have_no_gaps_or_duplicates(summary_df)
    add_check(results, array_size, "period no missing/no duplicate", no_gap_duplicate_ok, gap_detail)

    point_probes = set(point_df.get("probe", pd.Series(dtype=str)).astype(str))
    missing_probes = sorted(EXPECTED_PROBES - point_probes)
    extra_probes = sorted(point_probes - EXPECTED_PROBES)
    probe_count_ok = True
    if {"period", "probe"}.issubset(point_df.columns):
        per_period_probe_counts = point_df.groupby("period")["probe"].nunique()
        duplicated_period_probe = int(point_df.duplicated(["period", "probe"]).sum())
        probe_count_ok = bool(
            len(per_period_probe_counts) == 41
            and (per_period_probe_counts == len(EXPECTED_PROBES)).all()
            and duplicated_period_probe == 0
        )
    else:
        duplicated_period_probe = -1
        probe_count_ok = False
    add_check(
        results,
        array_size,
        "probe set contains P0-P4/front/rear",
        not missing_probes and not extra_probes and probe_count_ok,
        f"missing={missing_probes}, extra={extra_probes}, duplicated_period_probe={duplicated_period_probe}",
    )

    incident_ok = "incident_abs" in point_df.columns and np.allclose(
        pd.to_numeric(point_df["incident_abs"], errors="coerce"), 1.0, atol=1e-8, rtol=0.0
    )
    add_check(results, array_size, "incident_abs is 1.0", bool(incident_ok), "checked point_probes incident_abs")

    mesh_ok = True
    mesh_details: list[str] = []
    for label, dataframe in (("summary", summary_df), ("point", point_df)):
        if "mesh_level" not in dataframe.columns:
            mesh_ok = False
            mesh_details.append(f"{label}:missing mesh_level")
        else:
            values = sorted(set(dataframe["mesh_level"].astype(str)))
            mesh_ok = mesh_ok and values == ["medium"]
            mesh_details.append(f"{label}:{values}")
    add_check(results, array_size, "mesh_level is medium", mesh_ok, "; ".join(mesh_details))

    array_ok = True
    array_details: list[str] = []
    for label, dataframe in (("summary", summary_df), ("point", point_df)):
        if "array_size" not in dataframe.columns:
            array_ok = False
            array_details.append(f"{label}:missing array_size")
        else:
            values = sorted(set(pd.to_numeric(dataframe["array_size"], errors="coerce").dropna().astype(int)))
            array_ok = array_ok and values == [array_size]
            array_details.append(f"{label}:{values}")
    add_check(results, array_size, "array_size is correct", array_ok, "; ".join(array_details))

    return results


def build_metric_series(summary_df: pd.DataFrame, metric: str) -> pd.Series:
    """Return the requested centre metric series from a refined summary table."""
    if metric == "A_c_mean":
        return pd.to_numeric(summary_df["center_mean_abs"], errors="coerce")
    if metric == "A_c_max":
        return pd.to_numeric(summary_df["center_max_abs"], errors="coerce")
    if metric == "R_loc":
        if "R_loc" in summary_df.columns:
            return pd.to_numeric(summary_df["R_loc"], errors="coerce")
        return pd.to_numeric(summary_df["center_max_abs"], errors="coerce") / pd.to_numeric(
            summary_df["center_mean_abs"], errors="coerce"
        )
    raise ValueError(f"Unsupported metric: {metric}")


def make_peak_records(array_size: int, summary_df: pd.DataFrame) -> list[dict[str, object]]:
    """Build peak records without assigning physical resonance labels."""
    periods = pd.to_numeric(summary_df["period"], errors="coerce").round(3)
    records: list[dict[str, object]] = []
    source_file = str(refined_paths(array_size)["summary"])
    for metric in ("A_c_mean", "A_c_max", "R_loc"):
        values = build_metric_series(summary_df, metric)
        peak_index = int(values.idxmax())
        peak_period = float(periods.loc[peak_index])
        is_boundary_peak = bool(
            np.isclose(peak_period, 0.85) or np.isclose(peak_period, 1.05)
        )
        near_lower_boundary = bool(0.85 <= peak_period <= 0.87)
        records.append(
            {
                "array_size": array_size,
                "metric": metric,
                "peak_value": float(values.loc[peak_index]),
                "peak_period": peak_period,
                "is_boundary_peak": is_boundary_peak,
                "near_lower_boundary": near_lower_boundary,
                "boundary_peak_label": (
                    "refined-scan boundary peak" if is_boundary_peak else "interior peak"
                ),
                "lower_boundary_interval_label": (
                    "refined lower-boundary inspection interval"
                    if near_lower_boundary
                    else "outside lower-boundary inspection interval"
                ),
                "source_file": source_file,
            }
        )
    return records


def save_peak_table(all_summaries: dict[int, pd.DataFrame]) -> Path:
    records: list[dict[str, object]] = []
    for array_size, summary_df in all_summaries.items():
        records.extend(make_peak_records(array_size, summary_df))
    peak_df = pd.DataFrame(records)
    output_path = OUTPUT_DIR / "N468_refined_center_peak_table_0p85_1p05.csv"
    peak_df.to_csv(output_path, index=False, float_format="%.12g")
    print(f"Saved peak table: {output_path}")
    return output_path


def plot_metric(all_summaries: dict[int, pd.DataFrame], metric: str, ylabel: str, output_path: Path) -> None:
    """Plot one refined centre metric for all array sizes."""
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.0, 4.5), constrained_layout=True)
    for array_size in ARRAY_SIZES:
        summary_df = all_summaries[array_size].sort_values("period")
        x = pd.to_numeric(summary_df["period"], errors="coerce")
        y = build_metric_series(summary_df, metric)
        ax.plot(x, y, marker="o", markersize=3, linewidth=1.2, label=f"N={array_size}")
    ax.axvspan(0.85, 0.87, color="0.9", label="0.85-0.87 inspection")
    ax.set_xlabel("Period T (s)")
    ax.set_ylabel(ylabel)
    ax.set_xlim(0.85, 1.05)
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)
    print(f"Saved figure: {output_path}")


def print_checks(checks: list[CheckResult]) -> None:
    """Print required integrity checks to stdout."""
    print("\nRefined scan completeness checks")
    print("array_size,check,status,detail")
    for result in checks:
        print(f"N={result.array_size},{result.check},{result.status},{result.detail}")


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    FIGURE_DIR.mkdir(exist_ok=True)

    checks: list[CheckResult] = []
    summaries: dict[int, pd.DataFrame] = {}

    for array_size in ARRAY_SIZES:
        summary_df, point_df, existence_checks = read_refined_inputs(array_size)
        checks.extend(existence_checks)
        if summary_df is None or point_df is None:
            continue
        array_checks = validate_array(array_size, summary_df, point_df)
        checks.extend(array_checks)
        if all(check.status == "PASS" for check in array_checks):
            summaries[array_size] = summary_df

    print_checks(checks)
    failed = [check for check in checks if check.status != "PASS"]
    if failed:
        raise ValueError(
            "Refined scan completeness checks failed; fix input CSVs before plotting."
        )

    if set(summaries) != set(ARRAY_SIZES):
        raise ValueError("Missing validated refined summaries for one or more array sizes.")

    save_peak_table(summaries)
    plot_metric(
        summaries,
        "A_c_mean",
        "Centre mean |eta| (unit incident-wave amplitude)",
        FIGURE_DIR / "N468_refined_center_mean_0p85_1p05.png",
    )
    plot_metric(
        summaries,
        "A_c_max",
        "Centre max |eta| (unit incident-wave amplitude)",
        FIGURE_DIR / "N468_refined_center_max_0p85_1p05.png",
    )
    plot_metric(
        summaries,
        "R_loc",
        "Centre max-to-mean ratio",
        FIGURE_DIR / "N468_refined_center_max_to_mean_ratio_0p85_1p05.png",
    )

    print("Boundary rule: T=0.85 or T=1.05 is marked as a refined-scan boundary peak.")
    print("Lower-boundary inspection interval: T=0.85-0.87.")


if __name__ == "__main__":
    main()
