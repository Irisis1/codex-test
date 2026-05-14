import argparse
import glob
import os
import sys
from decimal import Decimal

import numpy as np
import pandas as pd

import capytaine as cpt
from capytaine.bem.airy_waves import airy_waves_free_surface_elevation
from capytaine.green_functions.abstract_green_function import (
    GreenFunctionEvaluationError,
)

OUTPUT_DIR = "outputs"
FIGURE_DIR = "figures"


# Physical parameters (SI units)
G = 9.81
RHO = 1000.0
WATER_DEPTH = 0.60

CYLINDER_RADIUS = 0.06
CYLINDER_DRAFT = 0.598
RING_RADIUS = 0.30


# Fixed probe definitions shared by all array sizes.
SMOKE_TEST_ARRAY_SIZES = (4, 6, 8)
SMOKE_TEST_PERIOD = 1.00

MESH_DIAGNOSTIC_ARRAY_SIZE = 8
MESH_LEVEL_RESOLUTIONS = {
    "coarse": (8, 8, 3),
    "base": (12, 12, 4),
    "medium": (16, 16, 6),
    "fine": (24, 24, 8),
}

# Stage 4 formal mesh selection for the N=8 production period sweep.
# The completed N=8 multi-period mesh-convergence results at T = 0.98,
# 1.00, 1.02, 1.36, 1.38, and 1.40 s showed that the medium mesh differs
# from the fine mesh by less than 2% for every representative period and key
# metric, while coarse/base/fine remain available above for mesh-convergence use.
FORMAL_MESH_LEVEL = "medium"
FORMAL_MESH_RESOLUTION = MESH_LEVEL_RESOLUTIONS[FORMAL_MESH_LEVEL]

MESH_CONVERGENCE_REPRESENTATIVE_PERIODS = (0.98, 1.00, 1.02, 1.36, 1.38, 1.40)


CANDIDATE_LINE_COORDINATES = (
    -0.40,
    -0.35,
    -0.30,
    -0.25,
    -0.20,
    -0.15,
    -0.10,
    0.10,
    0.15,
    0.20,
    0.25,
    0.30,
    0.35,
    0.40,
)


POINT_PROBES = (
    ("P0", 0.0, 0.0),
    ("P1", 0.1, 0.0),
    ("P2", -0.1, 0.0),
    ("P3", 0.0, 0.1),
    ("P4", 0.0, -0.1),
    ("front", -2.0, 0.0),
    ("rear", 2.0, 0.0),
)


def sampling_lines():
    """Return the horizontal line probes for smoke-test sampling.

    These line offsets are shared by the 4-, 6-, and 8-cylinder arrays and
    keep all smoke-test samples at least 0.01 m from every cylinder footprint.
    The vertical candidate ``cross_line_x0p4`` is intentionally not used as a
    formal smoke-test output line.
    """
    main_x = np.linspace(-1.5, 1.5, 21)

    main_line_y0p1 = [("main_line_y0p1", i, x, 0.1) for i, x in enumerate(main_x)]
    main_line_ym0p1 = [("main_line_ym0p1", i, x, -0.1) for i, x in enumerate(main_x)]
    return main_line_y0p1 + main_line_ym0p1


def ensure_output_dirs():
    """Create runtime directories for numerical outputs and figures."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(FIGURE_DIR, exist_ok=True)


def cylinder_centers(n, radius=RING_RADIUS):
    """Return equally spaced cylinder centers on a circular ring."""
    angles = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
    return [(radius * np.cos(theta), radius * np.sin(theta)) for theta in angles]


def make_fixed_cylinder(x, y, resolution=MESH_LEVEL_RESOLUTIONS["base"]):
    """Create one fixed vertical circular cylinder."""
    mesh = cpt.mesh_vertical_cylinder(
        radius=CYLINDER_RADIUS,
        length=CYLINDER_DRAFT,
        center=(x, y, -CYLINDER_DRAFT / 2.0),
        resolution=resolution,
    )

    body = cpt.FloatingBody(mesh=mesh)
    body.keep_immersed_part()
    return body


def make_ring_array(n, resolution=MESH_LEVEL_RESOLUTIONS["base"]):
    """Create a fixed n-cylinder ring array."""
    bodies = []

    for i, (x, y) in enumerate(cylinder_centers(n)):
        body = make_fixed_cylinder(x, y, resolution=resolution)
        body.name = f"cylinder_{i + 1}"
        bodies.append(body)

    array_body = bodies[0]
    for body in bodies[1:]:
        array_body = array_body + body

    array_body.name = f"ring_{n}_cylinders"
    return array_body


def mesh_diagnostics_dataframe(
    n=MESH_DIAGNOSTIC_ARRAY_SIZE, mesh_level_resolutions=MESH_LEVEL_RESOLUTIONS
):
    """Build ring-array meshes and report geometry-only mesh statistics.

    This diagnostic workflow intentionally does not instantiate a BEM solver,
    define diffraction problems, or run any period sweep. It only builds fixed
    N=8 ring-array meshes with alternate ``mesh_vertical_cylinder`` resolutions
    and summarizes their panel counts and panel areas.
    """
    records = []

    for mesh_level, cylinder_resolution in mesh_level_resolutions.items():
        body = make_ring_array(n, resolution=cylinder_resolution)
        mesh = body.mesh
        panel_areas = np.asarray(mesh.faces_areas, dtype=float)

        records.append(
            {
                "mesh_level": mesh_level,
                "cylinder_resolution": "x".join(
                    str(value) for value in cylinder_resolution
                ),
                "total_vertices": int(mesh.nb_vertices),
                "total_faces": int(mesh.nb_faces),
                "mean_panel_area": float(np.mean(panel_areas)),
                "min_panel_area": float(np.min(panel_areas)),
                "max_panel_area": float(np.max(panel_areas)),
            }
        )

    return pd.DataFrame(records)


def save_mesh_diagnostics_N8():
    """Save the N=8 mesh diagnostics table without running BEM."""
    ensure_output_dirs()
    output_path = os.path.join(OUTPUT_DIR, "mesh_diagnostics_N8.csv")
    mesh_diagnostics_dataframe().to_csv(output_path, index=False)
    print(f"Saved N=8 mesh diagnostics: {output_path}")
    return output_path


def clearance_status(clearance):
    """Classify a clearance against the geometry-only safety thresholds."""
    if clearance < 0.0:
        return "unsafe"
    if clearance < 0.01:
        return "near_surface"
    return "safe"


def minimum_clearance_to_cylinders(points, centers):
    """Return the minimum footprint clearance for samples against centers."""
    center_distances = np.linalg.norm(points[:, np.newaxis, :] - centers, axis=2)
    return float(np.min(center_distances) - CYLINDER_RADIUS)


def geometry_clearance_dataframe(array_sizes=SMOKE_TEST_ARRAY_SIZES):
    """Compute probe clearances from cylinder footprints for diagnostic review.

    Clearance is measured in the horizontal plane as the distance from each
    fixed probe sample to the nearest cylinder center minus the cylinder radius.
    Negative values identify samples inside a cylinder footprint. This helper
    only reports geometry and does not alter any physical or normalization
    parameters used by the diffraction smoke tests.
    """
    base_samples = [
        {
            "sample_type": "point",
            "sample_label": label,
            "sample_index": "",
            "x": x,
            "y": y,
        }
        for label, x, y in POINT_PROBES
    ]
    line_samples = [
        {
            "sample_type": "line",
            "sample_label": line_name,
            "sample_index": index,
            "x": x,
            "y": y,
        }
        for line_name, index, x, y in sampling_lines()
    ]

    records = []
    for n in array_sizes:
        centers = np.array(cylinder_centers(n), dtype=float)
        for sample in base_samples + line_samples:
            point = np.array((sample["x"], sample["y"]), dtype=float)
            center_distances = np.linalg.norm(centers - point, axis=1)
            nearest_index = int(np.argmin(center_distances))
            nearest_distance = float(center_distances[nearest_index])
            clearance = nearest_distance - CYLINDER_RADIUS
            nearest_center_x, nearest_center_y = centers[nearest_index]

            records.append(
                {
                    "array_size": n,
                    **sample,
                    "nearest_cylinder": nearest_index + 1,
                    "nearest_center_x": nearest_center_x,
                    "nearest_center_y": nearest_center_y,
                    "nearest_center_distance": nearest_distance,
                    "cylinder_radius": CYLINDER_RADIUS,
                    "clearance": clearance,
                    "inside_cylinder_footprint": clearance < 0.0,
                }
            )

    return pd.DataFrame(records)


def candidate_line_clearance_dataframe(array_sizes=SMOKE_TEST_ARRAY_SIZES):
    """Evaluate candidate safe horizontal and vertical measurement lines.

    The check is geometry-only: horizontal lines use 61 samples from x=-1.5 m
    to x=1.5 m, vertical lines use 61 samples from y=-1.0 m to y=1.0 m,
    and the reported clearance is the minimum over all requested array sizes.
    """
    records = []

    for y in CANDIDATE_LINE_COORDINATES:
        points = np.column_stack((np.linspace(-1.5, 1.5, 61), np.full(61, y)))
        per_array_clearance = {}
        for n in array_sizes:
            centers = np.array(cylinder_centers(n), dtype=float)
            per_array_clearance[f"min_clearance_N{n}"] = minimum_clearance_to_cylinders(
                points, centers
            )
        min_clearance = min(per_array_clearance.values())
        records.append(
            {
                "line_type": "horizontal",
                "line_label": f"y={y:+.2f}",
                "fixed_coordinate": y,
                "sample_axis": "x",
                "sample_start": -1.5,
                "sample_end": 1.5,
                "sample_count": 61,
                "min_clearance": min_clearance,
                "status": clearance_status(min_clearance),
                **per_array_clearance,
            }
        )

    for x in CANDIDATE_LINE_COORDINATES:
        points = np.column_stack((np.full(61, x), np.linspace(-1.0, 1.0, 61)))
        per_array_clearance = {}
        for n in array_sizes:
            centers = np.array(cylinder_centers(n), dtype=float)
            per_array_clearance[f"min_clearance_N{n}"] = minimum_clearance_to_cylinders(
                points, centers
            )
        min_clearance = min(per_array_clearance.values())
        records.append(
            {
                "line_type": "vertical",
                "line_label": f"x={x:+.2f}",
                "fixed_coordinate": x,
                "sample_axis": "y",
                "sample_start": -1.0,
                "sample_end": 1.0,
                "sample_count": 61,
                "min_clearance": min_clearance,
                "status": clearance_status(min_clearance),
                **per_array_clearance,
            }
        )

    return pd.DataFrame(records)


def save_candidate_line_clearance_check():
    """Save the geometry-only candidate line clearance diagnostic CSV."""
    ensure_output_dirs()
    output_path = os.path.join(OUTPUT_DIR, "candidate_line_clearance_check.csv")
    candidate_line_clearance_dataframe().to_csv(output_path, index=False)
    print(f"Saved candidate line clearance check: {output_path}")
    return output_path


def save_probe_geometry_clearance_check():
    """Save a geometry-only probe clearance diagnostic CSV.

    The generated file belongs under ``outputs/`` and is intentionally not
    produced by ``main()`` so routine smoke tests do not create this diagnostic
    unless it is requested explicitly.
    """
    ensure_output_dirs()
    output_path = os.path.join(OUTPUT_DIR, "probe_geometry_clearance_check.csv")
    geometry_clearance_dataframe().to_csv(output_path, index=False)
    print(f"Saved probe geometry clearance check: {output_path}")
    return output_path


def compute_diffracted_elevation(points, solver, result):
    """Compute diffracted elevation, preserving rows for invalid samples.

    Some shared smoke-test line samples can fall inside a cylinder footprint for
    a given array size. Those points are kept in the output with NaN diffracted
    and total elevation values instead of changing the common probe definition.
    """
    try:
        return solver.compute_free_surface_elevation(points, result)
    except GreenFunctionEvaluationError:
        eta_diffracted = np.full(len(points), np.nan + 1j * np.nan, dtype=complex)
        for i, point in enumerate(points):
            try:
                eta_diffracted[i] = solver.compute_free_surface_elevation(
                    point.reshape(1, 2), result
                )[0]
            except GreenFunctionEvaluationError:
                print(
                    "Warning: diffracted elevation is undefined at "
                    f"x={point[0]:.6g}, y={point[1]:.6g}; writing NaN."
                )
        return eta_diffracted


def free_surface_elevation_dataframe(samples, solver, result, problem):
    """Compute incident, diffracted, and total elevation for sample points.

    The body has no degrees of freedom, so the solved ``DiffractionProblem`` is
    fixed-body diffraction only. Capytaine's BEM post-processing returns the
    scattered/diffracted elevation from the solved source distribution; the
    undisturbed Airy-wave elevation is added to report the physical total
    elevation for Capytaine's unit incident-wave amplitude normalization.
    """
    points = np.array([(sample["x"], sample["y"]) for sample in samples], dtype=float)

    eta_diffracted = np.asarray(
        compute_diffracted_elevation(points, solver, result), dtype=complex
    )
    eta_incident = np.asarray(
        airy_waves_free_surface_elevation(points, problem), dtype=complex
    )
    eta_total = eta_incident + eta_diffracted

    records = []
    for sample, eta_i, eta_d, eta in zip(
        samples, eta_incident, eta_diffracted, eta_total
    ):
        records.append(
            {
                **sample,
                "incident_real": eta_i.real,
                "incident_imag": eta_i.imag,
                "incident_abs": abs(eta_i),
                "diffracted_real": eta_d.real,
                "diffracted_imag": eta_d.imag,
                "diffracted_abs": abs(eta_d),
                "total_real": eta.real,
                "total_imag": eta.imag,
                "total_abs": abs(eta),
            }
        )

    return pd.DataFrame(records)


def point_probe_dataframe(solver, result, problem):
    """Compute the fixed point-probe free-surface elevations."""
    samples = [{"probe": label, "x": x, "y": y} for label, x, y in POINT_PROBES]
    return free_surface_elevation_dataframe(samples, solver, result, problem)


def mesh_convergence_dataframe(n=MESH_DIAGNOSTIC_ARRAY_SIZE, period=SMOKE_TEST_PERIOD):
    """Run a single-period N=8 mesh-convergence smoke test.

    The workflow keeps the fixed-body diffraction-only physics and the shared
    point-probe definitions unchanged.  It runs only the requested array size
    and period for the four configured mesh levels, then reports point-probe
    elevations together with scalar convergence metrics referenced to the fine
    mesh.
    """
    records = []
    omega = 2.0 * np.pi / period

    for mesh_level, cylinder_resolution in MESH_LEVEL_RESOLUTIONS.items():
        body = make_ring_array(n, resolution=cylinder_resolution)
        total_faces = int(body.mesh.nb_faces)
        total_vertices = int(body.mesh.nb_vertices)

        solver = cpt.BEMSolver()
        problem = cpt.DiffractionProblem(
            body=body,
            omega=omega,
            water_depth=WATER_DEPTH,
            wave_direction=0.0,
            rho=RHO,
            g=G,
        )

        result = solver.solve(problem)
        point_df = point_probe_dataframe(solver, result, problem)
        total_abs_by_probe = point_df.set_index("probe")["total_abs"]

        center_total_abs = total_abs_by_probe.loc[["P0", "P1", "P2", "P3", "P4"]]
        front_abs = float(total_abs_by_probe.loc["front"])
        rear_abs = float(total_abs_by_probe.loc["rear"])

        record = {
            "array_size": n,
            "period": period,
            "mesh_level": mesh_level,
            "cylinder_resolution": "x".join(
                str(value) for value in cylinder_resolution
            ),
            "total_vertices": total_vertices,
            "total_faces": total_faces,
            "center_mean_abs": float(center_total_abs.mean()),
            "center_max_abs": float(center_total_abs.max()),
            "front_abs": front_abs,
            "rear_abs": rear_abs,
            "S_rear_front": rear_abs / front_abs,
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
                record[f"{probe}_{quantity}"] = probe_record[quantity]

        records.append(record)

    df = pd.DataFrame(records)
    fine_row = df.loc[df["mesh_level"] == "fine"].iloc[0]

    df["error_center_mean_percent"] = (
        (df["center_mean_abs"] - fine_row["center_mean_abs"]).abs()
        / abs(fine_row["center_mean_abs"])
        * 100.0
    )
    df["error_center_max_percent"] = (
        (df["center_max_abs"] - fine_row["center_max_abs"]).abs()
        / abs(fine_row["center_max_abs"])
        * 100.0
    )
    df["error_S_percent"] = (
        (df["S_rear_front"] - fine_row["S_rear_front"]).abs()
        / abs(fine_row["S_rear_front"])
        * 100.0
    )

    return df


def mesh_convergence_representative_periods_dataframe(
    n=MESH_DIAGNOSTIC_ARRAY_SIZE,
    periods=MESH_CONVERGENCE_REPRESENTATIVE_PERIODS,
):
    """Run the N=8 mesh-convergence checks at representative periods.

    This stage-3 workflow deliberately limits the BEM solves to the requested
    representative periods, uses the existing four mesh levels, and preserves
    all physical parameters plus fixed point-probe definitions. Error columns
    are computed by ``mesh_convergence_dataframe`` against the fine mesh within
    each individual period.
    """
    dataframes = [mesh_convergence_dataframe(n=n, period=period) for period in periods]
    return pd.concat(dataframes, ignore_index=True)


def save_mesh_convergence_N8_representative_periods():
    """Save the N=8 representative-period mesh-convergence CSV."""
    ensure_output_dirs()
    output_path = os.path.join(
        OUTPUT_DIR, "mesh_convergence_N8_representative_periods.csv"
    )
    df = mesh_convergence_representative_periods_dataframe(n=8)
    expected_rows = len(MESH_CONVERGENCE_REPRESENTATIVE_PERIODS) * len(
        MESH_LEVEL_RESOLUTIONS
    )
    if len(df) != expected_rows:
        raise ValueError(
            "Representative-period mesh convergence table has "
            f"{len(df)} rows; expected {expected_rows}."
        )
    if df.isna().any().any():
        nan_columns = df.columns[df.isna().any()].tolist()
        raise ValueError(f"NaN values found in columns: {nan_columns}")
    df.to_csv(output_path, index=False)
    print(f"Saved N=8 representative-period mesh convergence test: {output_path}")
    return output_path


def save_mesh_convergence_N8_T1p00():
    """Save the N=8, T=1.00 s mesh-convergence smoke-test CSV."""
    ensure_output_dirs()
    output_path = os.path.join(OUTPUT_DIR, "mesh_convergence_N8_T1p00.csv")
    mesh_convergence_dataframe(n=8, period=1.00).to_csv(output_path, index=False)
    print(f"Saved N=8 mesh convergence smoke test: {output_path}")
    return output_path


def line_probe_dataframe(solver, result, problem):
    """Compute the main and cross line free-surface elevations."""
    samples = [
        {"line": line_name, "sample_index": index, "x": x, "y": y}
        for line_name, index, x, y in sampling_lines()
    ]
    return free_surface_elevation_dataframe(samples, solver, result, problem)


def run_probe_smoke_test(n=4, period=SMOKE_TEST_PERIOD):
    """Run one fixed-body diffraction case and save free-surface probes."""
    ensure_output_dirs()

    body = make_ring_array(n)
    solver = cpt.BEMSolver()

    omega = 2.0 * np.pi / period
    problem = cpt.DiffractionProblem(
        body=body,
        omega=omega,
        water_depth=WATER_DEPTH,
        wave_direction=0.0,
        rho=RHO,
        g=G,
    )

    result = solver.solve(problem)
    point_df = point_probe_dataframe(solver, result, problem)
    line_df = line_probe_dataframe(solver, result, problem)

    output_stem = f"smoke_test_N{n}_T{period:.2f}".replace(".", "p")
    point_csv_path = os.path.join(OUTPUT_DIR, f"probe_{output_stem}.csv")
    line_csv_path = os.path.join(OUTPUT_DIR, f"line_{output_stem}.csv")
    point_df.to_csv(point_csv_path, index=False)
    line_df.to_csv(line_csv_path, index=False)

    print(
        f"Finished fixed-body diffraction probe smoke test: " f"N={n}, T={period:.2f} s"
    )
    print(f"Saved point probes: {point_csv_path}")
    print(f"Saved line probes: {line_csv_path}")

    return point_csv_path, line_csv_path


def run_all_smoke_tests():
    """Run small fixed-body diffraction smoke tests for all array sizes."""
    output_paths = []
    for n in SMOKE_TEST_ARRAY_SIZES:
        output_paths.append(run_probe_smoke_test(n=n, period=SMOKE_TEST_PERIOD))
    return output_paths


def period_token(value):
    """Format a period value for filenames, using ``p`` as decimal separator."""
    return f"{value:.2f}".replace(".", "p")


def segment_output_paths(start, end):
    """Return the three CSV paths for an N=8 period-scan segment."""
    segment_token = f"{period_token(start)}_{period_token(end)}"
    return {
        "summary": os.path.join(
            OUTPUT_DIR, f"N8_period_scan_summary_{segment_token}.csv"
        ),
        "point": os.path.join(
            OUTPUT_DIR, f"N8_period_scan_point_probes_{segment_token}.csv"
        ),
        "line": os.path.join(
            OUTPUT_DIR, f"N8_period_scan_line_probes_{segment_token}.csv"
        ),
    }


def periods_from_range(start, end, step):
    """Return an inclusive list of rounded periods from CLI decimal inputs."""
    start_decimal = Decimal(str(start))
    end_decimal = Decimal(str(end))
    step_decimal = Decimal(str(step))
    if step_decimal <= 0:
        raise ValueError("--step must be positive.")
    if start_decimal > end_decimal:
        raise ValueError("--start must be less than or equal to --end.")

    periods = []
    current = start_decimal
    tolerance = step_decimal / Decimal("1000000")
    while current <= end_decimal + tolerance:
        periods.append(float(current.quantize(Decimal("0.01"))))
        current += step_decimal
    return periods


def existing_periods_with_row_count(path, expected_rows_per_period):
    """Read period values that already have the expected number of CSV rows."""
    if not os.path.exists(path):
        return set()
    df = pd.read_csv(path)
    if "period" not in df.columns:
        return set()

    periods = df["period"].dropna().round(2)
    row_counts = periods.value_counts()
    return {
        round(float(period), 2)
        for period, row_count in row_counts.items()
        if row_count == expected_rows_per_period
    }


def completed_segment_periods(paths):
    """Return periods that already have complete summary, point, and line rows."""
    completed = (
        existing_periods_with_row_count(paths["summary"], 1)
        & existing_periods_with_row_count(paths["point"], len(POINT_PROBES))
        & existing_periods_with_row_count(paths["line"], len(sampling_lines()))
    )
    return completed


def append_dataframe(path, df):
    """Append a dataframe to a CSV, writing the header only for new files."""
    df.to_csv(path, mode="a", header=not os.path.exists(path), index=False)


def solve_period_scan_case(period):
    """Solve one N=8 medium-mesh fixed-body diffraction period-scan case."""
    body = make_ring_array(
        MESH_DIAGNOSTIC_ARRAY_SIZE, resolution=FORMAL_MESH_RESOLUTION
    )
    solver = cpt.BEMSolver()
    omega = 2.0 * np.pi / period
    problem = cpt.DiffractionProblem(
        body=body,
        omega=omega,
        water_depth=WATER_DEPTH,
        wave_direction=0.0,
        rho=RHO,
        g=G,
    )
    result = solver.solve(problem)

    point_df = point_probe_dataframe(solver, result, problem)
    line_df = line_probe_dataframe(solver, result, problem)
    point_df.insert(0, "period", period)
    line_df.insert(0, "period", period)

    total_abs_by_probe = point_df.set_index("probe")["total_abs"]
    center_total_abs = total_abs_by_probe.loc[["P0", "P1", "P2", "P3", "P4"]]
    front_abs = float(total_abs_by_probe.loc["front"])
    rear_abs = float(total_abs_by_probe.loc["rear"])
    summary_df = pd.DataFrame(
        [
            {
                "array_size": MESH_DIAGNOSTIC_ARRAY_SIZE,
                "period": period,
                "mesh_level": FORMAL_MESH_LEVEL,
                "cylinder_resolution": "x".join(
                    str(value) for value in FORMAL_MESH_RESOLUTION
                ),
                "total_vertices": int(body.mesh.nb_vertices),
                "total_faces": int(body.mesh.nb_faces),
                "center_mean_abs": float(center_total_abs.mean()),
                "center_max_abs": float(center_total_abs.max()),
                "front_abs": front_abs,
                "rear_abs": rear_abs,
                "S_rear_front": rear_abs / front_abs,
            }
        ]
    )
    return summary_df, point_df, line_df


def run_scan_segment(start, end, step):
    """Run an resumable N=8 medium-mesh period-scan segment."""
    ensure_output_dirs()
    periods = periods_from_range(start, end, step)
    paths = segment_output_paths(start, end)
    completed = completed_segment_periods(paths)

    for period in periods:
        rounded_period = round(period, 2)
        if rounded_period in completed:
            print(f"Skipping completed period T={period:.2f} s")
            continue

        print(f"Solving N=8 {FORMAL_MESH_LEVEL} mesh period T={period:.2f} s")
        summary_df, point_df, line_df = solve_period_scan_case(period)
        append_dataframe(paths["summary"], summary_df)
        append_dataframe(paths["point"], point_df)
        append_dataframe(paths["line"], line_df)
        completed.add(rounded_period)

    print(f"Saved N=8 period scan summary segment: {paths['summary']}")
    print(f"Saved N=8 period scan point-probe segment: {paths['point']}")
    print(f"Saved N=8 period scan line-probe segment: {paths['line']}")
    return paths


def segment_csv_paths(kind):
    """Find input segment CSVs for one period-scan output kind."""
    pattern = os.path.join(OUTPUT_DIR, f"N8_period_scan_{kind}_*_*.csv")
    final_path = os.path.join(OUTPUT_DIR, f"N8_period_scan_{kind}_0p90_2p00.csv")
    return sorted(path for path in glob.glob(pattern) if path != final_path)


def read_segment_data(kind):
    """Read and concatenate existing period-scan segment CSVs."""
    paths = segment_csv_paths(kind)
    if not paths:
        raise FileNotFoundError(f"No segment CSV files found for {kind}.")
    dataframes = [pd.read_csv(path) for path in paths]
    return pd.concat(dataframes, ignore_index=True)


def validate_no_nan(name, df):
    """Raise if a dataframe contains any NaN values."""
    if df.isna().any().any():
        columns = df.columns[df.isna().any()].tolist()
        raise ValueError(f"{name} contains NaN values in columns: {columns}")


def validate_merged_scan(summary_df, point_df, line_df):
    """Validate the merged N=8 period scan before saving final CSV files."""
    expected_periods = periods_from_range(0.90, 2.00, 0.01)
    expected_period_set = {round(period, 2) for period in expected_periods}
    summary_periods = [round(float(period), 2) for period in summary_df["period"]]

    if len(summary_periods) != len(set(summary_periods)):
        raise ValueError("Duplicate period values found in summary data.")
    if set(summary_periods) != expected_period_set:
        missing = sorted(expected_period_set - set(summary_periods))
        extra = sorted(set(summary_periods) - expected_period_set)
        raise ValueError(
            "Merged summary periods must cover 0.90 to 2.00 s exactly; "
            f"missing={missing}, extra={extra}"
        )
    if len(summary_periods) != 111:
        raise ValueError(
            f"Merged summary has {len(summary_periods)} periods; expected 111."
        )

    expected_point_rows = 111 * len(POINT_PROBES)
    expected_line_rows = 111 * len(sampling_lines())
    if len(point_df) != expected_point_rows:
        raise ValueError(
            f"Merged point-probe table has {len(point_df)} rows; "
            f"expected {expected_point_rows}."
        )
    if len(line_df) != expected_line_rows:
        raise ValueError(
            f"Merged line-probe table has {len(line_df)} rows; expected {expected_line_rows}."
        )

    if point_df.duplicated(subset=["period", "probe"]).any():
        raise ValueError("Duplicate period/probe rows found in point-probe data.")
    if line_df.duplicated(subset=["period", "line", "sample_index"]).any():
        raise ValueError(
            "Duplicate period/line/sample_index rows found in line-probe data."
        )

    point_period_set = {
        round(float(period), 2) for period in point_df["period"].unique()
    }
    line_period_set = {round(float(period), 2) for period in line_df["period"].unique()}
    if point_period_set != expected_period_set:
        raise ValueError("Point-probe periods do not cover 0.90 to 2.00 s exactly.")
    if line_period_set != expected_period_set:
        raise ValueError("Line-probe periods do not cover 0.90 to 2.00 s exactly.")

    validate_no_nan("summary", summary_df)
    validate_no_nan("point-probe", point_df)
    validate_no_nan("line-probe", line_df)


def merge_segments():
    """Merge existing N=8 period-scan segment CSV files into final outputs."""
    ensure_output_dirs()
    summary_df = read_segment_data("summary")
    point_df = read_segment_data("point_probes")
    line_df = read_segment_data("line_probes")

    summary_df["period"] = summary_df["period"].round(2)
    point_df["period"] = point_df["period"].round(2)
    line_df["period"] = line_df["period"].round(2)

    summary_df = summary_df.sort_values("period").reset_index(drop=True)
    point_df = point_df.sort_values(["period", "probe"]).reset_index(drop=True)
    line_df = line_df.sort_values(["period", "line", "sample_index"]).reset_index(
        drop=True
    )

    validate_merged_scan(summary_df, point_df, line_df)

    output_paths = segment_output_paths(0.90, 2.00)
    summary_df.to_csv(output_paths["summary"], index=False)
    point_df.to_csv(output_paths["point"], index=False)
    line_df.to_csv(output_paths["line"], index=False)

    print(f"Saved merged N=8 period scan summary: {output_paths['summary']}")
    print(f"Saved merged N=8 period scan point probes: {output_paths['point']}")
    print(f"Saved merged N=8 period scan line probes: {output_paths['line']}")
    return output_paths


def build_arg_parser():
    """Build the command-line parser for explicit simulation workflows."""
    parser = argparse.ArgumentParser(
        description=(
            "Run explicit Capytaine fixed-body diffraction workflows for "
            "circular-cylinder ring arrays."
        )
    )
    parser.add_argument(
        "--mode",
        choices=("mesh-diagnostics", "smoke-test", "scan-segment", "merge-segments"),
        help=(
            "Workflow to run. If omitted, this help is shown and no calculation "
            "is started."
        ),
    )
    parser.add_argument(
        "--start",
        type=float,
        default=0.90,
        help="Start period in seconds for --mode scan-segment (inclusive).",
    )
    parser.add_argument(
        "--end",
        type=float,
        default=1.20,
        help="End period in seconds for --mode scan-segment (inclusive).",
    )
    parser.add_argument(
        "--step",
        type=float,
        default=0.01,
        help="Period step in seconds for --mode scan-segment.",
    )
    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.mode is None:
        parser.print_help()
        return 2

    if args.mode == "mesh-diagnostics":
        save_mesh_diagnostics_N8()
    elif args.mode == "smoke-test":
        run_probe_smoke_test(n=4, period=SMOKE_TEST_PERIOD)
    elif args.mode == "scan-segment":
        run_scan_segment(start=args.start, end=args.end, step=args.step)
    elif args.mode == "merge-segments":
        merge_segments()
    else:
        parser.error(f"Unsupported mode: {args.mode}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
