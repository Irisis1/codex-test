"""Run the N=4/6/8 refined short-period point-probe scan.

This script deliberately keeps the main 0.90--2.00 s scan files untouched and
writes only refined 0.85--1.05 s CSV files.  It reuses the geometry, physics,
normalization, mesh settings, and point-probe post-processing helpers from
``run_ring_array.py``.  It does not call ``run_period_case`` because that helper
is tied to two-decimal periods and line-probe output for the broader scan; this
refined task needs three-decimal 0.005 s periods and point probes only.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

import run_ring_array as base

ARRAY_SIZES = (4, 6, 8)
REFINED_START_MILLISECOND = 850
REFINED_END_MILLISECOND = 1050
REFINED_STEP_MILLISECOND = 5
REFINED_PERIOD_DECIMALS = 3
OUTPUT_DIR = Path(base.OUTPUT_DIR)


def refined_periods() -> list[float]:
    """Return 0.850, 0.855, ..., 1.050 s using integer milliseconds."""
    periods = [
        round(milliseconds / 1000.0, REFINED_PERIOD_DECIMALS)
        for milliseconds in range(
            REFINED_START_MILLISECOND,
            REFINED_END_MILLISECOND + REFINED_STEP_MILLISECOND,
            REFINED_STEP_MILLISECOND,
        )
    ]
    if len(periods) != 41 or periods[0] != 0.85 or periods[-1] != 1.05:
        raise ValueError(f"Unexpected refined period sequence: {periods}")
    return periods


def output_paths(array_size: int) -> dict[str, Path]:
    """Return refined output paths for one array size."""
    return {
        "summary": OUTPUT_DIR
        / f"N{array_size}_refined_period_scan_summary_0p85_1p05.csv",
        "point": OUTPUT_DIR
        / f"N{array_size}_refined_period_scan_point_probes_0p85_1p05.csv",
    }


def read_existing_refined_csv(path: Path) -> pd.DataFrame:
    """Read an existing refined CSV, rounding periods to three decimals."""
    if not path.exists():
        return pd.DataFrame()
    dataframe = pd.read_csv(path)
    if "period" in dataframe.columns:
        dataframe["period"] = pd.to_numeric(dataframe["period"], errors="coerce").round(
            REFINED_PERIOD_DECIMALS
        )
    return dataframe


def completed_refined_periods(summary_df: pd.DataFrame, point_df: pd.DataFrame) -> set[float]:
    """Return periods complete in both summary and point-probe refined tables."""
    if summary_df.empty or point_df.empty:
        return set()

    summary_counts = summary_df.groupby("period").size()
    point_counts = point_df.groupby("period").size()

    completed: set[float] = set()
    for period, summary_count in summary_counts.items():
        if summary_count == 1 and point_counts.get(period, 0) == len(base.POINT_PROBES):
            completed.add(round(float(period), REFINED_PERIOD_DECIMALS))
    return completed


def drop_period_rows(dataframe: pd.DataFrame, period: float) -> pd.DataFrame:
    """Drop stale or partial rows for a refined period before recomputing it."""
    if dataframe.empty or "period" not in dataframe.columns:
        return dataframe
    period_values = pd.to_numeric(dataframe["period"], errors="coerce").round(
        REFINED_PERIOD_DECIMALS
    )
    return dataframe.loc[period_values != period].copy()


def save_refined_tables(
    paths: dict[str, Path], summary_df: pd.DataFrame, point_df: pd.DataFrame
) -> None:
    """Persist refined tables with deterministic ordering and compact periods."""
    if not summary_df.empty:
        summary_df.sort_values(["period"], inplace=True, ignore_index=True)
    if not point_df.empty:
        point_df.sort_values(["period", "probe"], inplace=True, ignore_index=True)

    summary_df.to_csv(paths["summary"], index=False, float_format="%.12g")
    point_df.to_csv(paths["point"], index=False, float_format="%.12g")


def run_refined_period_case(array_size: int, body, solver, period: float):
    """Run one fixed-body diffraction-only refined point-probe period."""
    omega = 2.0 * np.pi / period
    problem = base.cpt.DiffractionProblem(
        body=body,
        omega=omega,
        water_depth=base.WATER_DEPTH,
        wave_direction=0.0,
        rho=base.RHO,
        g=base.G,
    )

    result = solver.solve(problem)
    point_df = base.point_probe_dataframe(solver, result, problem)

    total_abs_by_probe = point_df.set_index("probe")["total_abs"]
    center_total_abs = total_abs_by_probe.loc[["P0", "P1", "P2", "P3", "P4"]]
    front_abs = float(total_abs_by_probe.loc["front"])
    rear_abs = float(total_abs_by_probe.loc["rear"])
    period_value = round(period, REFINED_PERIOD_DECIMALS)

    summary_record = {
        "array_size": array_size,
        "period": period_value,
        "omega": omega,
        "mesh_level": base.FORMAL_MESH_LEVEL,
        "cylinder_resolution": "x".join(str(value) for value in base.FORMAL_MESH_RESOLUTION),
        "total_vertices": int(body.mesh.nb_vertices),
        "total_faces": int(body.mesh.nb_faces),
        "center_mean_abs": float(center_total_abs.mean()),
        "center_max_abs": float(center_total_abs.max()),
        "front_abs": front_abs,
        "rear_abs": rear_abs,
        # Local rear/front amplitude ratio at fixed probes.
        "S_rear_front": rear_abs / front_abs,
        # Local centre peak-to-mean ratio for the fixed five centre probes.
        "R_loc": float(center_total_abs.max() / center_total_abs.mean()),
    }

    for probe_record in point_df.to_dict("records"):
        probe = probe_record["probe"]
        for quantity in (
            "incident_real",
            "incident_imag",
            "incident_abs",
            "diffracted_real",
            "diffracted_imag",
            "diffracted_abs",
            "total_real",
            "total_imag",
            "total_abs",
        ):
            summary_record[f"{probe}_{quantity}"] = probe_record[quantity]

    metadata = {
        "array_size": array_size,
        "period": period_value,
        "omega": omega,
        "mesh_level": base.FORMAL_MESH_LEVEL,
    }
    point_df = point_df.assign(**metadata)
    return pd.DataFrame([summary_record]), point_df


def run_refined_scan_for_array(array_size: int) -> dict[str, Path]:
    """Run or resume the refined point-probe scan for one array size."""
    base.ensure_output_dirs()
    periods = refined_periods()
    paths = output_paths(array_size)

    summary_df = read_existing_refined_csv(paths["summary"])
    point_df = read_existing_refined_csv(paths["point"])
    completed_periods = completed_refined_periods(summary_df, point_df)
    pending_periods = [period for period in periods if period not in completed_periods]

    print(
        f"N={array_size} refined point-probe scan 0.85-1.05 s, step=0.005 s: "
        f"{len(completed_periods)} completed, {len(pending_periods)} pending."
    )

    if pending_periods:
        body = base.make_ring_array(array_size, resolution=base.FORMAL_MESH_RESOLUTION)
        solver = base.cpt.BEMSolver()

        for period in pending_periods:
            print(f"Running N={array_size} refined fixed-body scan at T={period:.3f} s")
            new_summary_df, new_point_df = run_refined_period_case(
                array_size, body, solver, period
            )
            summary_df = drop_period_rows(summary_df, period)
            point_df = drop_period_rows(point_df, period)
            summary_df = pd.concat([summary_df, new_summary_df], ignore_index=True)
            point_df = pd.concat([point_df, new_point_df], ignore_index=True)
            save_refined_tables(paths, summary_df, point_df)
            print(f"Saved refined outputs through T={period:.3f} s")
    else:
        save_refined_tables(paths, summary_df, point_df)

    print(f"Saved N={array_size} refined summary: {paths['summary']}")
    print(f"Saved N={array_size} refined point probes: {paths['point']}")
    return paths


def main() -> None:
    for array_size in ARRAY_SIZES:
        run_refined_scan_for_array(array_size)


if __name__ == "__main__":
    main()
