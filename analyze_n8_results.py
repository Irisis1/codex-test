"""Strict diagnostics for the completed N=8 period-scan CSV files.

This script intentionally performs post-processing only. It reads the merged
N=8 period-scan CSV files already present in outputs/ and writes Chinese data
quality and interpretation diagnostics without running any Capytaine BEM solver,
without modifying the original CSV files, and without generating final figures.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

OUTPUT_DIR = Path("outputs")

SUMMARY_CSV = OUTPUT_DIR / "N8_period_scan_summary_0p90_2p00.csv"
POINT_CSV = OUTPUT_DIR / "N8_period_scan_point_probes_0p90_2p00.csv"
LINE_CSV = OUTPUT_DIR / "N8_period_scan_line_probes_0p90_2p00.csv"

REPORT_MD = OUTPUT_DIR / "N8_analysis_report.md"
KEY_METRICS_CSV = OUTPUT_DIR / "N8_key_metrics.csv"
BAND_PEAK_CSV = OUTPUT_DIR / "N8_band_peak_summary.csv"
CENTER_PROBE_CSV = OUTPUT_DIR / "N8_center_probe_summary.csv"
LINE_PROFILE_CSV = OUTPUT_DIR / "N8_line_profile_summary_selected_periods.csv"
PLOT_RECOMMENDATIONS_CSV = OUTPUT_DIR / "N8_plot_recommendations.csv"

TOLERANCE = 1e-6
EXPECTED_PERIODS = np.round(np.arange(0.90, 2.00 + 0.005, 0.01), 2)
EXPECTED_POINT_PROBES = {
    "P0": (0.0, 0.0),
    "P1": (0.1, 0.0),
    "P2": (-0.1, 0.0),
    "P3": (0.0, 0.1),
    "P4": (0.0, -0.1),
    "front": (-2.0, 0.0),
    "rear": (2.0, 0.0),
}
CENTER_PROBES = ["P0", "P1", "P2", "P3", "P4"]
POINT_PROBE_ORDER = CENTER_PROBES + ["front", "rear"]
EXPECTED_LINES = ["main_line_y0p1", "main_line_ym0p1"]
EXPECTED_LINE_Y = {"main_line_y0p1": 0.10, "main_line_ym0p1": -0.10}
EXPECTED_LINE_X = np.linspace(-1.5, 1.5, 21)
SUMMARY_REQUIRED_COLUMNS = [
    "period",
    "center_mean_abs",
    "center_max_abs",
    "front_abs",
    "rear_abs",
    "S_rear_front",
]
POINT_REQUIRED_COLUMNS = [
    "period",
    "probe",
    "x",
    "y",
    "incident_real",
    "incident_imag",
    "incident_abs",
    "diffracted_real",
    "diffracted_imag",
    "diffracted_abs",
    "total_real",
    "total_imag",
    "total_abs",
]
LINE_REQUIRED_COLUMNS = [
    "period",
    "line",
    "sample_index",
    "x",
    "y",
    "incident_real",
    "incident_imag",
    "incident_abs",
    "diffracted_real",
    "diffracted_imag",
    "diffracted_abs",
    "total_real",
    "total_imag",
    "total_abs",
]
KEY_METRICS = [
    "center_mean_abs",
    "center_max_abs",
    "front_abs",
    "rear_abs",
    "S_rear_front",
]
BANDS = [
    ("Band A", 0.90, 1.05, "中心增强候选区"),
    ("Band B", 1.30, 1.45, "后场响应或共振候选区"),
    ("Band C", 1.45, 2.00, "长周期响应区"),
]
SELECTED_PERIODS = [0.94, 1.00, 1.36, 1.38, 1.40]


@dataclass
class ValidationResult:
    name: str
    status: str
    detail: str


def status_text(condition: bool) -> str:
    return "PASS" if condition else "FAIL"


def format_float(value: float, digits: int = 6) -> str:
    if pd.isna(value):
        return "NaN"
    return f"{float(value):.{digits}f}"


def require_input_files() -> None:
    missing = [path for path in (SUMMARY_CSV, POINT_CSV, LINE_CSV) if not path.exists()]
    if missing:
        missing_text = "\n".join(f"- {path}" for path in missing)
        raise FileNotFoundError(
            "缺少 N=8 已合并周期扫描 CSV，无法生成数据诊断报告。"
            "请先把以下原始 CSV 放入 outputs/，本脚本不会生成或修改这些原始文件：\n"
            f"{missing_text}"
        )


def read_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    require_input_files()
    summary_df = pd.read_csv(SUMMARY_CSV)
    point_df = pd.read_csv(POINT_CSV)
    line_df = pd.read_csv(LINE_CSV)
    for dataframe in (summary_df, point_df, line_df):
        if "period" in dataframe.columns:
            dataframe["period"] = pd.to_numeric(dataframe["period"], errors="coerce")
            dataframe["period"] = dataframe["period"].round(2)
    return summary_df, point_df, line_df


def numeric_columns(required_columns: list[str], label_columns: set[str]) -> list[str]:
    return [column for column in required_columns if column not in label_columns]


def has_nonfinite(dataframe: pd.DataFrame, columns: list[str]) -> bool:
    numeric = dataframe[columns].apply(pd.to_numeric, errors="coerce")
    return bool(numeric.isna().any().any() or ~np.isfinite(numeric.to_numpy()).all())


def period_sequence_ok(periods: pd.Series) -> bool:
    values = np.sort(pd.to_numeric(periods, errors="coerce").to_numpy(dtype=float))
    return len(values) == len(EXPECTED_PERIODS) and np.allclose(
        values, EXPECTED_PERIODS, atol=TOLERANCE, rtol=0.0
    )


def validate_summary(summary_df: pd.DataFrame) -> list[ValidationResult]:
    results: list[ValidationResult] = []
    results.append(ValidationResult("summary exists", "PASS", str(SUMMARY_CSV)))
    missing_columns = [c for c in SUMMARY_REQUIRED_COLUMNS if c not in summary_df.columns]
    results.append(
        ValidationResult(
            "summary required columns",
            status_text(not missing_columns),
            "missing=" + str(missing_columns),
        )
    )
    if missing_columns:
        return results

    results.append(
        ValidationResult(
            "summary row count",
            status_text(len(summary_df) == 111),
            f"actual={len(summary_df)}, expected=111",
        )
    )
    period_values = pd.to_numeric(summary_df["period"], errors="coerce")
    results.append(
        ValidationResult(
            "summary period range",
            status_text(
                np.isclose(period_values.min(), 0.90, atol=TOLERANCE)
                and np.isclose(period_values.max(), 2.00, atol=TOLERANCE)
            ),
            f"min={format_float(period_values.min(), 2)}, max={format_float(period_values.max(), 2)}",
        )
    )
    sorted_periods = np.sort(period_values.to_numpy(dtype=float))
    period_diffs = np.diff(sorted_periods)
    step_ok = len(period_diffs) == 110 and np.allclose(
        period_diffs, 0.01, atol=TOLERANCE, rtol=0.0
    )
    results.append(
        ValidationResult(
            "summary period step",
            status_text(step_ok and period_sequence_ok(summary_df["period"])),
            "expected 0.01 from 0.90 to 2.00",
        )
    )
    duplicates = summary_df["period"].duplicated().sum()
    results.append(
        ValidationResult("summary duplicate period", status_text(duplicates == 0), f"duplicates={duplicates}")
    )
    results.append(
        ValidationResult(
            "summary finite numeric",
            status_text(not has_nonfinite(summary_df, SUMMARY_REQUIRED_COLUMNS)),
            "checked required numeric columns",
        )
    )
    negative_counts = {
        metric: int((pd.to_numeric(summary_df[metric], errors="coerce") < -TOLERANCE).sum())
        for metric in KEY_METRICS
    }
    results.append(
        ValidationResult(
            "summary non-negative responses",
            status_text(all(count == 0 for count in negative_counts.values())),
            str(negative_counts),
        )
    )
    return results


def validate_points(point_df: pd.DataFrame) -> list[ValidationResult]:
    results: list[ValidationResult] = [ValidationResult("point exists", "PASS", str(POINT_CSV))]
    missing_columns = [c for c in POINT_REQUIRED_COLUMNS if c not in point_df.columns]
    results.append(
        ValidationResult("point required columns", status_text(not missing_columns), "missing=" + str(missing_columns))
    )
    if missing_columns:
        return results

    results.append(
        ValidationResult("point row count", status_text(len(point_df) == 777), f"actual={len(point_df)}, expected=777")
    )
    expected_probe_set = set(POINT_PROBE_ORDER)
    period_probe_counts = point_df.groupby("period")["probe"].apply(lambda values: set(values))
    bad_periods = [period for period, probes in period_probe_counts.items() if probes != expected_probe_set]
    results.append(
        ValidationResult(
            "point probes per period",
            status_text(not bad_periods and len(period_probe_counts) == 111),
            f"bad_period_count={len(bad_periods)}",
        )
    )
    numeric = numeric_columns(POINT_REQUIRED_COLUMNS, {"probe"})
    results.append(
        ValidationResult("point finite numeric", status_text(not has_nonfinite(point_df, numeric)), "checked required numeric columns")
    )
    duplicates = int(point_df.duplicated(["period", "probe"]).sum())
    results.append(
        ValidationResult("point duplicate period-probe", status_text(duplicates == 0), f"duplicates={duplicates}")
    )
    coordinate_mismatches: list[str] = []
    for probe, (expected_x, expected_y) in EXPECTED_POINT_PROBES.items():
        rows = point_df.loc[point_df["probe"] == probe]
        if rows.empty:
            coordinate_mismatches.append(f"{probe}: missing")
            continue
        x_ok = np.allclose(rows["x"].astype(float), expected_x, atol=TOLERANCE, rtol=0.0)
        y_ok = np.allclose(rows["y"].astype(float), expected_y, atol=TOLERANCE, rtol=0.0)
        if not (x_ok and y_ok):
            coordinate_mismatches.append(f"{probe}: expected=({expected_x},{expected_y})")
    results.append(
        ValidationResult("point coordinates", status_text(not coordinate_mismatches), "; ".join(coordinate_mismatches) or "match AGENTS.md")
    )
    return results


def validate_lines(line_df: pd.DataFrame) -> list[ValidationResult]:
    results: list[ValidationResult] = [ValidationResult("line exists", "PASS", str(LINE_CSV))]
    missing_columns = [c for c in LINE_REQUIRED_COLUMNS if c not in line_df.columns]
    results.append(
        ValidationResult("line required columns", status_text(not missing_columns), "missing=" + str(missing_columns))
    )
    if missing_columns:
        return results

    results.append(
        ValidationResult("line row count", status_text(len(line_df) == 4662), f"actual={len(line_df)}, expected=4662")
    )
    line_sets = line_df.groupby("period")["line"].apply(lambda values: set(values))
    bad_line_periods = [period for period, lines in line_sets.items() if lines != set(EXPECTED_LINES)]
    results.append(
        ValidationResult(
            "line names per period",
            status_text(not bad_line_periods and len(line_sets) == 111),
            f"bad_period_count={len(bad_line_periods)}",
        )
    )
    counts = line_df.groupby(["period", "line"])["sample_index"].nunique()
    bad_counts = counts[counts != 21]
    results.append(
        ValidationResult("line sample count", status_text(bad_counts.empty), f"bad_groups={len(bad_counts)}")
    )
    numeric = numeric_columns(LINE_REQUIRED_COLUMNS, {"line"})
    results.append(
        ValidationResult("line finite numeric", status_text(not has_nonfinite(line_df, numeric)), "checked required numeric columns")
    )
    duplicates = int(line_df.duplicated(["period", "line", "sample_index"]).sum())
    results.append(
        ValidationResult("line duplicate period-line-sample", status_text(duplicates == 0), f"duplicates={duplicates}")
    )

    coordinate_mismatches: list[str] = []
    for line_name, expected_y in EXPECTED_LINE_Y.items():
        rows = line_df.loc[line_df["line"] == line_name]
        if rows.empty:
            coordinate_mismatches.append(f"{line_name}: missing")
            continue
        y_ok = np.allclose(rows["y"].astype(float), expected_y, atol=TOLERANCE, rtol=0.0)
        if not y_ok:
            coordinate_mismatches.append(f"{line_name}: y mismatch")
        for period, group in rows.groupby("period"):
            ordered = group.sort_values("sample_index")
            index_ok = np.array_equal(ordered["sample_index"].astype(int).to_numpy(), np.arange(21))
            x_ok = np.allclose(ordered["x"].astype(float).to_numpy(), EXPECTED_LINE_X, atol=TOLERANCE, rtol=0.0)
            if not (index_ok and x_ok):
                coordinate_mismatches.append(f"{line_name} T={period:.2f}: x/sample mismatch")
                break
    results.append(
        ValidationResult("line coordinates", status_text(not coordinate_mismatches), "; ".join(coordinate_mismatches) or "match required two horizontal lines")
    )
    return results


def metric_extrema(summary_df: pd.DataFrame) -> pd.DataFrame:
    records = []
    for metric in KEY_METRICS:
        series = pd.to_numeric(summary_df[metric], errors="coerce")
        max_idx = series.idxmax()
        min_idx = series.idxmin()
        mean_value = float(series.mean())
        max_value = float(series.loc[max_idx])
        min_value = float(series.loc[min_idx])
        value_range = max_value - min_value
        records.append(
            {
                "metric": metric,
                "max_value": max_value,
                "max_period": float(summary_df.loc[max_idx, "period"]),
                "min_value": min_value,
                "min_period": float(summary_df.loc[min_idx, "period"]),
                "mean": mean_value,
                "std": float(series.std(ddof=1)),
                "range": value_range,
                "relative_range": value_range / mean_value if mean_value != 0.0 else np.nan,
            }
        )
    return pd.DataFrame(records)


def local_peak_character(values: pd.Series) -> str:
    array = values.to_numpy(dtype=float)
    if len(array) < 3:
        return "样本不足，不能判断峰型"
    diffs = np.diff(array)
    increasing = np.all(diffs >= -TOLERANCE)
    decreasing = np.all(diffs <= TOLERANCE)
    if increasing:
        return "单调上升，不应强行称为 resonance peak"
    if decreasing:
        return "单调下降，不应强行称为 resonance peak"
    max_pos = int(np.argmax(array))
    if 0 < max_pos < len(array) - 1:
        left_rise = array[max_pos] - array[0]
        right_drop = array[max_pos] - array[-1]
        scale = max(abs(float(np.mean(array))), TOLERANCE)
        if left_rise / scale > 0.02 and right_drop / scale > 0.02:
            return "存在内部局部峰值候选，但仍需结合空间分布谨慎解释"
    if np.nanmax(array) - np.nanmin(array) <= 0.02 * max(abs(float(np.nanmean(array))), TOLERANCE):
        return "缓慢平台，无明确局部峰值"
    return "非单调缓变或边界峰值，不应直接称为 resonance peak"


def band_peak_summary(summary_df: pd.DataFrame) -> pd.DataFrame:
    records = []
    for band_name, start, end, description in BANDS:
        band_df = summary_df.loc[(summary_df["period"] >= start - TOLERANCE) & (summary_df["period"] <= end + TOLERANCE)].copy()
        record = {
            "band": band_name,
            "period_start": start,
            "period_end": end,
            "description": description,
            "trend_judgement": local_peak_character(band_df["center_mean_abs"]),
        }
        for metric in ["center_mean_abs", "center_max_abs", "rear_abs", "S_rear_front"]:
            idx = band_df[metric].idxmax()
            record[f"{metric}_local_max"] = float(band_df.loc[idx, metric])
            record[f"{metric}_local_max_period"] = float(band_df.loc[idx, "period"])
        s_idx = band_df["S_rear_front"].idxmax()
        record["front_abs_at_S_rear_front_local_max"] = float(band_df.loc[s_idx, "front_abs"])
        records.append(record)
    return pd.DataFrame(records)


def center_probe_analysis(point_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, float]]:
    center_df = point_df.loc[point_df["probe"].isin(CENTER_PROBES), ["period", "probe", "total_abs"]].copy()
    pivot = center_df.pivot(index="period", columns="probe", values="total_abs").sort_index()

    probe_records = []
    for probe in CENTER_PROBES:
        series = pivot[probe]
        max_idx = series.idxmax()
        min_idx = series.idxmin()
        probe_records.append(
            {
                "probe": probe,
                "max_total_abs": float(series.loc[max_idx]),
                "max_period": float(max_idx),
                "min_total_abs": float(series.loc[min_idx]),
                "min_period": float(min_idx),
                "mean_total_abs": float(series.mean()),
            }
        )
    summary = pd.DataFrame(probe_records)

    p1_p2_diff = (pivot["P1"] - pivot["P2"]).abs()
    p1_p2_rel = p1_p2_diff / pivot[["P1", "P2"]].mean(axis=1)
    p3_p4_diff = (pivot["P3"] - pivot["P4"]).abs()
    p3_p4_rel = p3_p4_diff / pivot[["P3", "P4"]].mean(axis=1)
    center_std = pivot[CENTER_PROBES].std(axis=1, ddof=1)
    center_mean = pivot[CENTER_PROBES].mean(axis=1)
    center_cv = center_std / center_mean

    diagnostic = pd.DataFrame(
        {
            "period": pivot.index,
            "P1_P2_abs_diff": p1_p2_diff.values,
            "P1_P2_relative_diff": p1_p2_rel.values,
            "P3_P4_abs_diff": p3_p4_diff.values,
            "P3_P4_relative_diff": p3_p4_rel.values,
            "center_std_abs": center_std.values,
            "center_cv_abs": center_cv.values,
        }
    )
    stats = {
        "P1_P2_max_abs_diff": float(p1_p2_diff.max()),
        "P1_P2_max_abs_diff_period": float(p1_p2_diff.idxmax()),
        "P1_P2_max_relative_diff": float(p1_p2_rel.max()),
        "P1_P2_max_relative_diff_period": float(p1_p2_rel.idxmax()),
        "P3_P4_max_abs_diff": float(p3_p4_diff.max()),
        "P3_P4_max_abs_diff_period": float(p3_p4_diff.idxmax()),
        "P3_P4_max_relative_diff": float(p3_p4_rel.max()),
        "P3_P4_max_relative_diff_period": float(p3_p4_rel.idxmax()),
        "center_cv_abs_max": float(center_cv.max()),
        "center_cv_abs_max_period": float(center_cv.idxmax()),
    }
    return summary, diagnostic, stats


def center_ratio_analysis(summary_df: pd.DataFrame) -> pd.DataFrame:
    ratio = summary_df["center_max_abs"] / summary_df["center_mean_abs"]
    return pd.DataFrame(
        [
            {
                "metric": "ratio_center_max_to_mean",
                "max_value": float(ratio.max()),
                "max_period": float(summary_df.loc[ratio.idxmax(), "period"]),
                "min_value": float(ratio.min()),
                "min_period": float(summary_df.loc[ratio.idxmin(), "period"]),
                "mean": float(ratio.mean()),
                "std": float(ratio.std(ddof=1)),
            }
        ]
    )


def front_rear_consistency(summary_df: pd.DataFrame) -> dict[str, float | str]:
    rear_corr = float(summary_df["rear_abs"].corr(summary_df["S_rear_front"], method="pearson"))
    front_corr = float(summary_df["front_abs"].corr(summary_df["S_rear_front"], method="pearson"))
    rear_idx = summary_df["rear_abs"].idxmax()
    s_idx = summary_df["S_rear_front"].idxmax()
    front_at_s = float(summary_df.loc[s_idx, "front_abs"])
    front_quantile_10 = float(summary_df["front_abs"].quantile(0.10))
    rear_at_s = float(summary_df.loc[s_idx, "rear_abs"])
    rear_quantile_90 = float(summary_df["rear_abs"].quantile(0.90))
    if front_at_s <= front_quantile_10 and rear_at_s < rear_quantile_90:
        driver = "front_abs lowered; ratio-amplification risk"
    elif rear_at_s >= rear_quantile_90 and front_at_s > front_quantile_10:
        driver = "rear_abs increased"
    else:
        driver = "mixed control; inspect front_abs, rear_abs, and S_rear_front together"
    return {
        "rear_S_pearson": rear_corr,
        "front_S_pearson": front_corr,
        "rear_max_period": float(summary_df.loc[rear_idx, "period"]),
        "rear_max_value": float(summary_df.loc[rear_idx, "rear_abs"]),
        "S_at_rear_max": float(summary_df.loc[rear_idx, "S_rear_front"]),
        "S_max_period": float(summary_df.loc[s_idx, "period"]),
        "S_max_value": float(summary_df.loc[s_idx, "S_rear_front"]),
        "rear_abs_at_S_max": rear_at_s,
        "front_abs_at_S_max": front_at_s,
        "front_abs_10pct": front_quantile_10,
        "rear_abs_90pct": rear_quantile_90,
        "S_peak_driver": driver,
    }


def nearest_periods(line_df: pd.DataFrame) -> dict[float, float]:
    available = np.sort(line_df["period"].unique())
    return {target: float(available[np.argmin(np.abs(available - target))]) for target in SELECTED_PERIODS}


def peak_location_class(x_value: float) -> str:
    if x_value < -0.1:
        return "迎浪侧偏移"
    if x_value > 0.1:
        return "背浪侧偏移"
    return "中心附近"


def line_profile_analysis(line_df: pd.DataFrame) -> tuple[pd.DataFrame, dict[float, float], str]:
    period_map = nearest_periods(line_df)
    records = []
    mean_peak_x_by_period = []
    for target_period, actual_period in period_map.items():
        period_df = line_df.loc[np.isclose(line_df["period"], actual_period, atol=TOLERANCE)].copy()
        line_stats = {}
        for line_name in EXPECTED_LINES:
            group = period_df.loc[period_df["line"] == line_name].sort_values("sample_index")
            max_idx = group["total_abs"].idxmax()
            min_idx = group["total_abs"].idxmin()
            max_x = float(group.loc[max_idx, "x"])
            line_stats[line_name] = {
                "max_total_abs": float(group.loc[max_idx, "total_abs"]),
                "max_x": max_x,
                "min_total_abs": float(group.loc[min_idx, "total_abs"]),
                "min_x": float(group.loc[min_idx, "x"]),
                "line_mean_abs": float(group["total_abs"].mean()),
                "line_std_abs": float(group["total_abs"].std(ddof=1)),
                "peak_location_class": peak_location_class(max_x),
            }
        plus = period_df.loc[period_df["line"] == "main_line_y0p1"].sort_values("x")
        minus = period_df.loc[period_df["line"] == "main_line_ym0p1"].sort_values("x")
        merged = plus[["x", "total_abs"]].merge(
            minus[["x", "total_abs"]], on="x", suffixes=("_y0p1", "_ym0p1")
        )
        diff = (merged["total_abs_y0p1"] - merged["total_abs_ym0p1"]).abs()
        pair_mean = merged[["total_abs_y0p1", "total_abs_ym0p1"]].mean(axis=1)
        relative_diff = diff / pair_mean.replace(0.0, np.nan)
        max_diff = float(diff.max())
        mean_diff = float(diff.mean())
        max_relative_diff = float(relative_diff.max())
        mean_relative_diff = float(relative_diff.mean())
        symmetry = "近似对称" if max_relative_diff <= 0.05 else "存在明显上下线差异"
        mean_peak_x = float(np.mean([line_stats[line]["max_x"] for line in EXPECTED_LINES]))
        mean_peak_x_by_period.append((actual_period, mean_peak_x))
        for line_name, stats in line_stats.items():
            records.append(
                {
                    "target_period": target_period,
                    "actual_period": actual_period,
                    "line": line_name,
                    **stats,
                    "paired_max_abs_diff": max_diff,
                    "paired_mean_abs_diff": mean_diff,
                    "paired_max_relative_diff": max_relative_diff,
                    "paired_mean_relative_diff": mean_relative_diff,
                    "symmetry_judgement": symmetry,
                }
            )
    peak_x_values = np.array([item[1] for item in mean_peak_x_by_period], dtype=float)
    peak_x_diffs = np.diff(peak_x_values)
    if len(peak_x_diffs) and np.all(peak_x_diffs > TOLERANCE):
        movement = "峰值位置随 period 近似向 +x 移动"
    elif len(peak_x_diffs) and np.all(peak_x_diffs < -TOLERANCE):
        movement = "峰值位置随 period 近似向 -x 移动"
    else:
        movement = "峰值位置无明确单调移动趋势，不应写 energy shifts downstream"
    return pd.DataFrame(records), period_map, movement


def jump_check_dataframe(dataframe: pd.DataFrame, value_columns: list[str], label: str) -> pd.DataFrame:
    records = []
    sorted_df = dataframe.sort_values("period").reset_index(drop=True)
    for column in value_columns:
        delta = sorted_df[column].diff().iloc[1:]
        intervals_start = sorted_df["period"].iloc[:-1].to_numpy(dtype=float)
        intervals_end = sorted_df["period"].iloc[1:].to_numpy(dtype=float)
        abs_delta = delta.abs().to_numpy(dtype=float)
        max_pos = int(np.nanargmax(abs_delta)) if len(abs_delta) else 0
        threshold = float(np.nanmean(abs_delta) + 4.0 * np.nanstd(abs_delta, ddof=1)) if len(abs_delta) > 1 else np.nan
        anomaly_positions = np.where(abs_delta > threshold)[0] if np.isfinite(threshold) else np.array([], dtype=int)
        if len(anomaly_positions) == 0:
            records.append(
                {
                    "table": label,
                    "metric": column,
                    "max_abs_delta": float(abs_delta[max_pos]) if len(abs_delta) else np.nan,
                    "max_delta_interval": f"{intervals_start[max_pos]:.2f}-{intervals_end[max_pos]:.2f}" if len(abs_delta) else "",
                    "threshold": threshold,
                    "anomaly_count": 0,
                    "anomaly_intervals": "",
                }
            )
        else:
            intervals = [f"{intervals_start[pos]:.2f}-{intervals_end[pos]:.2f}" for pos in anomaly_positions]
            records.append(
                {
                    "table": label,
                    "metric": column,
                    "max_abs_delta": float(abs_delta[max_pos]),
                    "max_delta_interval": f"{intervals_start[max_pos]:.2f}-{intervals_end[max_pos]:.2f}",
                    "threshold": threshold,
                    "anomaly_count": int(len(anomaly_positions)),
                    "anomaly_intervals": "; ".join(intervals),
                }
            )
    return pd.DataFrame(records)


def center_probe_jump_checks(point_df: pd.DataFrame) -> pd.DataFrame:
    pivot = point_df.loc[point_df["probe"].isin(CENTER_PROBES)].pivot(index="period", columns="probe", values="total_abs")
    return jump_check_dataframe(pivot.reset_index(), CENTER_PROBES, "point_center_total_abs")


def plot_recommendations(
    center_peak_periods_match: bool,
    rear_s_peak_match: bool,
    center_uniform: bool,
    has_2d_field_data: bool = False,
) -> pd.DataFrame:
    rows = [
        {
            "figure_name": "N8_center_five_points_0p90_2p00",
            "recommended": "yes",
            "reason": "用于检验 P0-P4 的峰值周期和幅值是否一致，避免把中心响应过度概括为单点行为。",
            "results_position": "Results 中 N=8 中心响应讨论的第一组辅助图或补充图。",
            "data_columns": "point_probes: period, probe, total_abs for P0-P4",
            "supports": "支持中心五点空间一致性、P0 是否为主峰值点、中心响应非均匀性判断。",
            "does_not_support": "不能支持严格能量透射、远场反射/透射系数或二维云图结论。",
        },
        {
            "figure_name": "N8_center_summary_0p90_2p00",
            "recommended": "yes",
            "reason": "center_mean_abs 与 center_max_abs 代表不同中心指标，应并列展示。",
            "results_position": "Results 中全周期关键响应概览。",
            "data_columns": "summary: period, center_mean_abs, center_max_abs",
            "supports": "支持中心平均响应与局部最大响应的峰值周期、幅值差异和局部非均匀性讨论。",
            "does_not_support": "若峰值周期不同，不能用单一中心指标代表全部中心响应。" if not center_peak_periods_match else "不能说明前后场 transmission-like indicator 的成因。",
        },
        {
            "figure_name": "N8_front_rear_S_0p90_2p00",
            "recommended": "yes",
            "reason": "S_rear_front 是 rear_abs/front_abs 的 transmission-like indicator，必须与 front_abs、rear_abs 联合解释。",
            "results_position": "Results 中前后场响应与 ratio 指标解释部分。",
            "data_columns": "summary: period, front_abs, rear_abs, S_rear_front",
            "supports": "支持判断 S_rear_front 峰值由后场增强、前场降低或二者共同作用控制。",
            "does_not_support": "不能单独支持严格 transmission coefficient 或 Kt；尤其当 rear_abs 与 S_rear_front 峰值不一致时更不能过度解释。" if not rear_s_peak_match else "不能替代能量通量一致的远场透射系数。",
        },
        {
            "figure_name": "N8_line_profiles_selected_periods",
            "recommended": "yes",
            "reason": "重点周期两条水平测线能展示局部峰值位置、上下线对称性和空间分布变化。",
            "results_position": "Results 中关键周期空间结构讨论。",
            "data_columns": "line_probes: period, line, sample_index, x, y, total_abs at selected periods",
            "supports": "支持测线上的峰值位置、上下 y=±0.10 m 线差异、是否存在明确移动趋势。",
            "does_not_support": "不能支持二维自由面云图形态；若无单调移动趋势，不能写 energy shifts downstream。",
        },
        {
            "figure_name": "N8_key_period_map_or_table",
            "recommended": "table" if not has_2d_field_data else "yes",
            "reason": "当前脚本只读取点探针和两条测线 CSV；没有二维自由面网格数据时应先做关键周期表格。",
            "results_position": "Results 中关键周期汇总，或作为最终二维图前的表格依据。",
            "data_columns": "summary key metrics, center probe total_abs, selected line profile summaries",
            "supports": "支持关键周期选择和跨指标对照。",
            "does_not_support": "没有二维网格数据时不能虚构二维云图或空间等值线。",
        },
        {
            "figure_name": "N8_mesh_convergence_table",
            "recommended": "yes",
            "reason": "用于方法或验证部分说明正式 N=8 扫描网格选择的可靠性。",
            "results_position": "Methods/Validation 或 Results 前的数值验证小节。",
            "data_columns": "mesh convergence tables if available: mesh_level, faces, center/rear/S metrics and relative differences",
            "supports": "支持网格收敛性和 medium mesh 选择。",
            "does_not_support": "不能由本 N=8 响应 CSV 单独证明；需要独立网格收敛数据。",
        },
    ]
    if not center_uniform:
        rows[0]["reason"] += " 当前判断提示中心不应表述为 uniform central amplification。"
    return pd.DataFrame(rows)



def dataframe_to_markdown(dataframe: pd.DataFrame, floatfmt: str | None = None) -> str:
    """Return a GitHub-style markdown table without requiring tabulate."""
    if dataframe.empty:
        return "（无记录）"
    columns = list(dataframe.columns)
    rows = ["| " + " | ".join(str(column) for column in columns) + " |"]
    rows.append("|" + "|".join("---" for _ in columns) + "|")
    for _, row in dataframe.iterrows():
        values = []
        for column in columns:
            value = row[column]
            if isinstance(value, (float, np.floating)) and floatfmt is not None:
                values.append(format(value, floatfmt))
            else:
                text = "" if pd.isna(value) else str(value)
                values.append(text.replace("|", "\\|"))
        rows.append("| " + " | ".join(values) + " |")
    return "\n".join(rows)

def validation_markdown(results: list[ValidationResult]) -> str:
    rows = ["| 检查项 | 状态 | 说明 |", "|---|---:|---|"]
    for result in results:
        rows.append(f"| {result.name} | {result.status} | {result.detail} |")
    return "\n".join(rows)


def write_report(
    validation_results: list[ValidationResult],
    key_metrics: pd.DataFrame,
    band_summary: pd.DataFrame,
    center_summary: pd.DataFrame,
    center_diagnostic_stats: dict[str, float],
    center_ratio: pd.DataFrame,
    front_rear: dict[str, float | str],
    line_summary: pd.DataFrame,
    selected_period_map: dict[float, float],
    line_movement: str,
    jump_summary: pd.DataFrame,
    plot_recs: pd.DataFrame,
) -> None:
    center_mean_peak = key_metrics.loc[key_metrics["metric"] == "center_mean_abs"].iloc[0]
    center_max_peak = key_metrics.loc[key_metrics["metric"] == "center_max_abs"].iloc[0]
    rear_peak = key_metrics.loc[key_metrics["metric"] == "rear_abs"].iloc[0]
    s_peak = key_metrics.loc[key_metrics["metric"] == "S_rear_front"].iloc[0]
    center_peak_match = np.isclose(center_mean_peak["max_period"], center_max_peak["max_period"], atol=TOLERANCE)
    rear_s_peak_match = np.isclose(rear_peak["max_period"], s_peak["max_period"], atol=TOLERANCE)
    center_probe_peak_periods = center_summary["max_period"].to_list()
    center_probe_peaks_match = len(set(np.round(center_probe_peak_periods, 2))) == 1
    p0_row = center_summary.loc[center_summary["probe"] == "P0"].iloc[0]
    p0_is_main_peak = bool(np.isclose(p0_row["max_total_abs"], center_summary["max_total_abs"].max(), atol=TOLERANCE))
    center_uniform = center_diagnostic_stats["center_cv_abs_max"] <= 0.05
    ratio_row = center_ratio.iloc[0]
    jump_anomalies = jump_summary.loc[jump_summary["anomaly_count"] > 0]

    selected_lines = []
    for target, actual in selected_period_map.items():
        suffix = "" if np.isclose(target, actual, atol=TOLERANCE) else "（使用最接近周期）"
        selected_lines.append(f"- T={target:.2f} s -> actual={actual:.2f} s{suffix}")

    text = f"""# N=8 周期扫描结果数据诊断报告

本报告由 `analyze_n8_results.py` 生成，仅读取既有 CSV，不运行 `solver.solve(...)`，不修改原始 outputs CSV，也不生成最终论文图。所有中心响应、前后场响应和测线空间分布判断均基于 `total_abs`；`diffracted_abs` 仅可作为散射贡献参考。`S_rear_front = rear_abs / front_abs` 在本报告中只称为 transmission-like indicator，不称为严格 transmission coefficient 或 Kt。

## 1. 数据完整性检查

{validation_markdown(validation_results)}

## 2. 全周期关键指标识别

{dataframe_to_markdown(key_metrics, '.6f')}

- `center_mean_abs` 最大周期为 T={center_mean_peak['max_period']:.2f} s，`center_max_abs` 最大周期为 T={center_max_peak['max_period']:.2f} s；二者{'一致' if center_peak_match else '不一致'}。
- `rear_abs` 最大周期为 T={rear_peak['max_period']:.2f} s，`S_rear_front` 最大周期为 T={s_peak['max_period']:.2f} s；二者{'一致' if rear_s_peak_match else '不一致'}。
- `S_rear_front` 峰值成因判断：{front_rear['S_peak_driver']}。若标记为 ratio-amplification risk，则不得解释为严格透射增强。

## 3. 频带分区分析

{dataframe_to_markdown(band_summary, '.6f')}

说明：频带内如果仅表现为单调变化、边界峰值或缓慢平台，报告不将其强行称为 resonance peak。

## 4. 中心五点空间一致性分析

{dataframe_to_markdown(center_summary, '.6f')}

- P0-P4 峰值周期{'一致' if center_probe_peaks_match else '不一致'}。
- P0 {'是' if p0_is_main_peak else '不是'}五点中 `total_abs` 的主要峰值点。
- P1/P2 最大绝对差为 {center_diagnostic_stats['P1_P2_max_abs_diff']:.6f}，发生在 T={center_diagnostic_stats['P1_P2_max_abs_diff_period']:.2f} s；最大相对差为 {center_diagnostic_stats['P1_P2_max_relative_diff']:.6f}，发生在 T={center_diagnostic_stats['P1_P2_max_relative_diff_period']:.2f} s。
- P3/P4 最大绝对差为 {center_diagnostic_stats['P3_P4_max_abs_diff']:.6f}，发生在 T={center_diagnostic_stats['P3_P4_max_abs_diff_period']:.2f} s；最大相对差为 {center_diagnostic_stats['P3_P4_max_relative_diff']:.6f}，发生在 T={center_diagnostic_stats['P3_P4_max_relative_diff_period']:.2f} s。
- `center_cv_abs` 最大值为 {center_diagnostic_stats['center_cv_abs_max']:.6f}，发生在 T={center_diagnostic_stats['center_cv_abs_max_period']:.2f} s。
- 中心增强空间均匀性判断：{'P0-P4 差异较小，可谨慎描述为空间近似一致' if center_uniform else 'P0-P4 差异明显，应避免使用 uniform central amplification 这类表述'}。

## 5. 中心平均响应与局部最大响应关系

{dataframe_to_markdown(center_ratio, '.6f')}

- `ratio_center_max_to_mean` 最大值为 {ratio_row['max_value']:.6f}，发生在 T={ratio_row['max_period']:.2f} s；最小值为 {ratio_row['min_value']:.6f}，发生在 T={ratio_row['min_period']:.2f} s；平均值为 {ratio_row['mean']:.6f}。
- {'由于 center_mean_abs 与 center_max_abs 峰值周期不同，论文中不能只用单一中心指标代表全部中心响应。' if not center_peak_match else '二者峰值周期一致，但仍建议同时绘制以展示平均响应与局部最大响应的幅值差异。'}
- 建议同时绘制 `center_mean_abs` 和 `center_max_abs`。

## 6. front/rear 与 S_rear_front 物理一致性检查

- `rear_abs` 与 `S_rear_front` 的 Pearson correlation = {front_rear['rear_S_pearson']:.6f}。
- `front_abs` 与 `S_rear_front` 的 Pearson correlation = {front_rear['front_S_pearson']:.6f}。
- `rear_abs` 最大处：T={front_rear['rear_max_period']:.2f} s，rear_abs={front_rear['rear_max_value']:.6f}，该处 S_rear_front={front_rear['S_at_rear_max']:.6f}。
- `S_rear_front` 最大处：T={front_rear['S_max_period']:.2f} s，S_rear_front={front_rear['S_max_value']:.6f}，该处 rear_abs={front_rear['rear_abs_at_S_max']:.6f}，front_abs={front_rear['front_abs_at_S_max']:.6f}。
- 控制因素判断：{front_rear['S_peak_driver']}。
- {'`S_rear_front` 与 `front_abs` 强负相关，不能单独作为透射增强证据。' if front_rear['front_S_pearson'] < -0.70 else '`S_rear_front` 仍不能单独作为严格透射增强证据，需与 front_abs、rear_abs 联合解释。'}
- 建议把 `front_abs`、`rear_abs` 和 `S_rear_front` 放在同一组图中。

## 7. 两条水平测线空间分布分析

重点周期匹配：
{chr(10).join(selected_lines)}

{dataframe_to_markdown(line_summary, '.6f')}

- 峰值位置移动判断：{line_movement}。
- 若表中 `symmetry_judgement` 显示上下线差异明显，应避免把 y=+0.10 m 与 y=-0.10 m 简化为完全对称响应。

## 8. 异常跳变检查

{dataframe_to_markdown(jump_summary, '.6f')}

{'未发现满足 abs(delta) > mean(abs(delta)) + 4*std(abs(delta)) 的异常跳变，曲线连续性通过初步检查。' if jump_anomalies.empty else '发现异常跳变，需复查上述 anomaly_intervals 中的 period interval 和对应指标。'}

## 9. 推荐画图清单

{dataframe_to_markdown(plot_recs)}
"""
    REPORT_MD.write_text(text, encoding="utf-8")


def main() -> None:
    summary_df, point_df, line_df = read_inputs()
    validation_results = []
    validation_results.extend(validate_summary(summary_df))
    validation_results.extend(validate_points(point_df))
    validation_results.extend(validate_lines(line_df))

    key_metrics = metric_extrema(summary_df)
    band_summary = band_peak_summary(summary_df)
    center_summary, _center_diagnostics, center_stats = center_probe_analysis(point_df)
    center_ratio = center_ratio_analysis(summary_df)
    front_rear = front_rear_consistency(summary_df)
    line_summary, period_map, line_movement = line_profile_analysis(line_df)
    summary_jumps = jump_check_dataframe(summary_df, KEY_METRICS, "summary")
    point_jumps = center_probe_jump_checks(point_df)
    jump_summary = pd.concat([summary_jumps, point_jumps], ignore_index=True)

    center_peak_match = np.isclose(
        key_metrics.loc[key_metrics["metric"] == "center_mean_abs", "max_period"].iloc[0],
        key_metrics.loc[key_metrics["metric"] == "center_max_abs", "max_period"].iloc[0],
        atol=TOLERANCE,
    )
    rear_s_peak_match = np.isclose(
        key_metrics.loc[key_metrics["metric"] == "rear_abs", "max_period"].iloc[0],
        key_metrics.loc[key_metrics["metric"] == "S_rear_front", "max_period"].iloc[0],
        atol=TOLERANCE,
    )
    center_uniform = center_stats["center_cv_abs_max"] <= 0.05
    plot_recs = plot_recommendations(center_peak_match, rear_s_peak_match, center_uniform)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    key_metrics.to_csv(KEY_METRICS_CSV, index=False)
    band_summary.to_csv(BAND_PEAK_CSV, index=False)
    center_summary.to_csv(CENTER_PROBE_CSV, index=False)
    line_summary.to_csv(LINE_PROFILE_CSV, index=False)
    plot_recs.to_csv(PLOT_RECOMMENDATIONS_CSV, index=False)
    write_report(
        validation_results,
        key_metrics,
        band_summary,
        center_summary,
        center_stats,
        center_ratio,
        front_rear,
        line_summary,
        period_map,
        line_movement,
        jump_summary,
        plot_recs,
    )

    print(f"Wrote report: {REPORT_MD}")
    print(f"Wrote key metrics: {KEY_METRICS_CSV}")
    print(f"Wrote band summary: {BAND_PEAK_CSV}")
    print(f"Wrote center probe summary: {CENTER_PROBE_CSV}")
    print(f"Wrote line profile summary: {LINE_PROFILE_CSV}")
    print(f"Wrote plot recommendations: {PLOT_RECOMMENDATIONS_CSV}")


if __name__ == "__main__":
    main()
