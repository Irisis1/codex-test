import argparse
import glob
import os

import numpy as np
import pandas as pd

import capytaine as cpt
from capytaine.bem.airy_waves import airy_waves_free_surface_elevation
from capytaine.green_functions.abstract_green_function import (
    GreenFunctionEvaluationError,
)

OUTPUT_DIR = "outputs"
FIGURE_DIR = "figures"

N8_SCAN_ARRAY_SIZE = 8
N8_SCAN_START_PERIOD = 0.90
N8_SCAN_END_PERIOD = 2.00
N8_SCAN_STEP = 0.01
N8_SCAN_PERIOD_DECIMALS = 2


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

FIELD_PLOT_DEFAULT_ARRAY_SIZE = 4
FIELD_PLOT_DEFAULT_PERIOD = 1.00
FIELD_PLOT_DEFAULT_X_LIMITS = (-1.5, 1.5)
FIELD_PLOT_DEFAULT_Y_LIMITS = (-1.0, 1.0)
FIELD_PLOT_DEFAULT_GRID_SHAPE = (121, 81)


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


def solve_fixed_body_diffraction_case(
    n,
    period,
    resolution=FORMAL_MESH_RESOLUTION,
    mesh_level=FORMAL_MESH_LEVEL,
):
    """Build and solve one fixed-body diffraction case with shared settings."""
    body = make_ring_array(n, resolution=resolution)
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
    return solver, problem, result, mesh_level


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
            "cylinder_resolution": "x".join(str(value) for value in cylinder_resolution),
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
    dataframes = [
        mesh_convergence_dataframe(n=n, period=period) for period in periods
    ]
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


def format_period_for_filename(period):
    """Format a period value for stable scan-segment filenames."""
    return f"{period:.2f}".replace(".", "p")


def period_sequence(start_period, end_period, step=N8_SCAN_STEP):
    """Return an inclusive, rounded period sequence for scan workflows."""
    if step <= 0.0:
        raise ValueError("Period step must be positive.")
    start_index = int(round(start_period / step))
    end_index = int(round(end_period / step))
    if end_index < start_index:
        raise ValueError("end_period must be greater than or equal to start_period.")
    return [
        round(index * step, N8_SCAN_PERIOD_DECIMALS)
        for index in range(start_index, end_index + 1)
    ]


def period_scan_paths(array_size, start_period, end_period):
    """Return the three CSV paths for one period-scan segment."""
    start_label = format_period_for_filename(start_period)
    end_label = format_period_for_filename(end_period)
    suffix = f"{start_label}_{end_label}"
    return {
        "summary": os.path.join(OUTPUT_DIR, f"N{array_size}_period_scan_summary_{suffix}.csv"),
        "point": os.path.join(OUTPUT_DIR, f"N{array_size}_period_scan_point_probes_{suffix}.csv"),
        "line": os.path.join(OUTPUT_DIR, f"N{array_size}_period_scan_line_probes_{suffix}.csv"),
    }


def read_existing_scan_csv(path):
    """Read an existing scan CSV, or return an empty DataFrame."""
    if not os.path.exists(path):
        return pd.DataFrame()

    dataframe = pd.read_csv(path)
    if "period" in dataframe.columns:
        dataframe["period"] = dataframe["period"].round(N8_SCAN_PERIOD_DECIMALS)
    return dataframe


def completed_segment_periods(summary_df, point_df, line_df):
    """Return periods already complete in all three segment output tables."""
    if summary_df.empty or point_df.empty or line_df.empty:
        return set()

    summary_counts = summary_df.groupby("period").size()
    point_counts = point_df.groupby("period").size()
    line_counts = line_df.groupby("period").size()

    completed = set()
    for period, summary_count in summary_counts.items():
        if (
            summary_count == 1
            and point_counts.get(period, 0) == len(POINT_PROBES)
            and line_counts.get(period, 0) == len(sampling_lines())
        ):
            completed.add(round(float(period), N8_SCAN_PERIOD_DECIMALS))
    return completed


def save_scan_tables(paths, summary_df, point_df, line_df):
    """Persist scan tables with deterministic ordering."""
    sort_specs = (
        (summary_df, ["period"]),
        (point_df, ["period", "probe"]),
        (line_df, ["period", "line", "sample_index"]),
    )
    for dataframe, sort_columns in sort_specs:
        if not dataframe.empty:
            dataframe.sort_values(sort_columns, inplace=True, ignore_index=True)

    summary_df.to_csv(paths["summary"], index=False)
    point_df.to_csv(paths["point"], index=False)
    line_df.to_csv(paths["line"], index=False)


def drop_period_rows(dataframe, period):
    """Drop stale or partial rows for a period before recomputing it."""
    if dataframe.empty or "period" not in dataframe.columns:
        return dataframe
    period_values = dataframe["period"].round(N8_SCAN_PERIOD_DECIMALS)
    return dataframe.loc[period_values != period].copy()


def run_period_case(array_size, body, solver, period):
    """Run one fixed-body diffraction-only scan period."""
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

    total_abs_by_probe = point_df.set_index("probe")["total_abs"]
    center_total_abs = total_abs_by_probe.loc[["P0", "P1", "P2", "P3", "P4"]]
    front_abs = float(total_abs_by_probe.loc["front"])
    rear_abs = float(total_abs_by_probe.loc["rear"])

    summary_record = {
        "array_size": array_size,
        "period": round(period, N8_SCAN_PERIOD_DECIMALS),
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
        "period": round(period, N8_SCAN_PERIOD_DECIMALS),
        "mesh_level": FORMAL_MESH_LEVEL,
    }
    point_df = point_df.assign(**metadata)
    line_df = line_df.assign(**metadata)

    return pd.DataFrame([summary_record]), point_df, line_df


def run_period_scan_segment(array_size, start_period, end_period, step=N8_SCAN_STEP):
    """Run a resumable period-scan segment and write segment CSV files.

    Existing segment CSVs are read before the run. Periods that already have one
    summary row, all fixed point probes, and all fixed line probes are skipped so
    interrupted local runs can resume without repeating completed BEM solves.
    """
    ensure_output_dirs()
    periods = period_sequence(start_period, end_period, step=step)
    paths = period_scan_paths(array_size, periods[0], periods[-1])

    summary_df = read_existing_scan_csv(paths["summary"])
    point_df = read_existing_scan_csv(paths["point"])
    line_df = read_existing_scan_csv(paths["line"])
    completed_periods = completed_segment_periods(summary_df, point_df, line_df)
    pending_periods = [period for period in periods if period not in completed_periods]

    print(
        f"N={array_size} period scan segment "
        f"{periods[0]:.2f}-{periods[-1]:.2f} s: "
        f"{len(completed_periods)} completed, {len(pending_periods)} pending."
    )

    if pending_periods:
        body = make_ring_array(array_size, resolution=FORMAL_MESH_RESOLUTION)
        solver = cpt.BEMSolver()

        for period in pending_periods:
            print(f"Running N={array_size} fixed-body diffraction scan at T={period:.2f} s")
            new_summary_df, new_point_df, new_line_df = run_period_case(array_size,
                body, solver, period
            )
            summary_df = drop_period_rows(summary_df, period)
            point_df = drop_period_rows(point_df, period)
            line_df = drop_period_rows(line_df, period)
            summary_df = pd.concat([summary_df, new_summary_df], ignore_index=True)
            point_df = pd.concat([point_df, new_point_df], ignore_index=True)
            line_df = pd.concat([line_df, new_line_df], ignore_index=True)
            save_scan_tables(paths, summary_df, point_df, line_df)
            print(f"Saved resumable segment outputs through T={period:.2f} s")
    else:
        save_scan_tables(paths, summary_df, point_df, line_df)

    print(f"Saved N={array_size} scan segment summary: {paths['summary']}")
    print(f"Saved N={array_size} scan segment point probes: {paths['point']}")
    print(f"Saved N={array_size} scan segment line probes: {paths['line']}")
    return paths


def scan_segment_glob(array_size, kind):
    """Return sorted segment CSV paths for a scan table kind, excluding merged outputs."""
    merged_path = os.path.join(
        OUTPUT_DIR,
        f"N{array_size}_period_scan_{kind}_{format_period_for_filename(N8_SCAN_START_PERIOD)}_"
        f"{format_period_for_filename(N8_SCAN_END_PERIOD)}.csv",
    )
    pattern = os.path.join(OUTPUT_DIR, f"N{array_size}_period_scan_{kind}_*.csv")
    return sorted(path for path in glob.glob(pattern) if path != merged_path)


def merged_period_scan_paths(array_size):
    """Return the final merged period-scan CSV paths."""
    start_label = format_period_for_filename(N8_SCAN_START_PERIOD)
    end_label = format_period_for_filename(N8_SCAN_END_PERIOD)
    suffix = f"{start_label}_{end_label}"
    return {
        "summary": os.path.join(OUTPUT_DIR, f"N{array_size}_period_scan_summary_{suffix}.csv"),
        "point": os.path.join(OUTPUT_DIR, f"N{array_size}_period_scan_point_probes_{suffix}.csv"),
        "line": os.path.join(OUTPUT_DIR, f"N{array_size}_period_scan_line_probes_{suffix}.csv"),
    }


def read_segment_tables(array_size, kind):
    """Read and concatenate all segment CSVs for one scan table kind."""
    paths = scan_segment_glob(array_size, kind)
    if not paths:
        raise FileNotFoundError(f"No segment CSV files found for {kind}.")
    return pd.concat((pd.read_csv(path) for path in paths), ignore_index=True), paths


def validate_merged_scan_tables(array_size, summary_df, point_df, line_df):
    """Validate the merged full 0.90-2.00 s scan tables."""
    expected_periods = period_sequence(
        N8_SCAN_START_PERIOD, N8_SCAN_END_PERIOD, step=N8_SCAN_STEP
    )
    expected_period_set = set(expected_periods)

    rounded_summary_periods = summary_df["period"].round(N8_SCAN_PERIOD_DECIMALS)
    if set(rounded_summary_periods) != expected_period_set:
        missing = sorted(expected_period_set - set(rounded_summary_periods))
        extra = sorted(set(rounded_summary_periods) - expected_period_set)
        raise ValueError(
            "Merged summary periods do not cover 0.90-2.00 s: "
            f"missing={missing}, extra={extra}"
        )
    if rounded_summary_periods.duplicated().any():
        duplicates = sorted(
            rounded_summary_periods[rounded_summary_periods.duplicated()].unique()
        )
        raise ValueError(f"Duplicate summary periods found: {duplicates}")
    if len(expected_periods) != 111 or len(summary_df) != 111:
        raise ValueError(
            f"Merged summary has {len(summary_df)} period rows; expected 111."
        )

    if (
        summary_df.isna().any().any()
        or point_df.isna().any().any()
        or line_df.isna().any().any()
    ):
        raise ValueError("NaN values found in merged scan tables.")

    for label, dataframe in (("summary", summary_df), ("point", point_df), ("line", line_df)):
        if "array_size" not in dataframe.columns:
            raise ValueError(f"Merged {label} table is missing array_size column.")
        rounded_sizes = set(dataframe["array_size"].astype(int))
        if rounded_sizes != {array_size}:
            raise ValueError(
                f"Merged {label} table has array_size values {sorted(rounded_sizes)}; expected {[array_size]}."
            )

    expected_point_rows = len(expected_periods) * len(POINT_PROBES)
    expected_line_rows = len(expected_periods) * len(sampling_lines())
    if len(point_df) != expected_point_rows:
        raise ValueError(
            "Merged point probes have "
            f"{len(point_df)} rows; expected {expected_point_rows}."
        )
    if len(line_df) != expected_line_rows:
        raise ValueError(
            f"Merged line probes have {len(line_df)} rows; expected {expected_line_rows}."
        )

    for label, dataframe, rows_per_period in (
        ("point", point_df, len(POINT_PROBES)),
        ("line", line_df, len(sampling_lines())),
    ):
        rounded_periods = dataframe["period"].round(N8_SCAN_PERIOD_DECIMALS)
        if set(rounded_periods) != expected_period_set:
            raise ValueError(f"Merged {label} periods do not cover 0.90-2.00 s.")
        counts = rounded_periods.value_counts()
        bad_counts = counts[counts != rows_per_period]
        if not bad_counts.empty:
            raise ValueError(
                f"Merged {label} table has incorrect rows per period: "
                f"{bad_counts.to_dict()}"
            )


def merge_period_scan_segments(array_size):
    """Merge validated period-scan segment CSVs into full-scan CSVs."""
    ensure_output_dirs()
    summary_df, summary_paths = read_segment_tables(array_size, "summary")
    point_df, point_paths = read_segment_tables(array_size, "point_probes")
    line_df, line_paths = read_segment_tables(array_size, "line_probes")

    summary_df["period"] = summary_df["period"].round(N8_SCAN_PERIOD_DECIMALS)
    point_df["period"] = point_df["period"].round(N8_SCAN_PERIOD_DECIMALS)
    line_df["period"] = line_df["period"].round(N8_SCAN_PERIOD_DECIMALS)

    summary_df.sort_values(["period"], inplace=True, ignore_index=True)
    point_df.sort_values(["period", "probe"], inplace=True, ignore_index=True)
    line_df.sort_values(
        ["period", "line", "sample_index"], inplace=True, ignore_index=True
    )

    validate_merged_scan_tables(array_size, summary_df, point_df, line_df)

    paths = merged_period_scan_paths(array_size)
    summary_df.to_csv(paths["summary"], index=False)
    point_df.to_csv(paths["point"], index=False)
    line_df.to_csv(paths["line"], index=False)

    print(f"Merged summary segments ({len(summary_paths)} files): {paths['summary']}")
    print(f"Merged point-probe segments ({len(point_paths)} files): {paths['point']}")
    print(f"Merged line-probe segments ({len(line_paths)} files): {paths['line']}")
    return paths


def line_probe_dataframe(solver, result, problem):
    """Compute the main and cross line free-surface elevations."""
    samples = [
        {"line": line_name, "sample_index": index, "x": x, "y": y}
        for line_name, index, x, y in sampling_lines()
    ]
    return free_surface_elevation_dataframe(samples, solver, result, problem)



def field_plot_grid(
    x_limits=FIELD_PLOT_DEFAULT_X_LIMITS,
    y_limits=FIELD_PLOT_DEFAULT_Y_LIMITS,
    grid_shape=FIELD_PLOT_DEFAULT_GRID_SHAPE,
):
    """Return a moderate 2D grid for selected-period free-surface plots."""
    nx, ny = grid_shape
    if nx <= 1 or ny <= 1:
        raise ValueError("Field-plot grid dimensions must both be greater than 1.")
    x = np.linspace(x_limits[0], x_limits[1], nx)
    y = np.linspace(y_limits[0], y_limits[1], ny)
    grid_x, grid_y = np.meshgrid(x, y)
    points = np.column_stack((grid_x.ravel(), grid_y.ravel()))
    return x, y, grid_x, grid_y, points


def free_surface_field_dataframe(solver, result, problem, points):
    """Compute selected-period incident, diffracted, and total elevations on a grid.

    This helper is intentionally separate from the scan workflows so dense 2D
    fields are only evaluated when ``--mode field-plot`` is explicitly selected.
    The normalization remains Capytaine's unit incident-wave amplitude.
    """
    eta_diffracted = np.asarray(
        compute_diffracted_elevation(points, solver, result), dtype=complex
    )
    eta_incident = np.asarray(
        airy_waves_free_surface_elevation(points, problem), dtype=complex
    )
    eta_total = eta_incident + eta_diffracted

    return pd.DataFrame(
        {
            "x": points[:, 0],
            "y": points[:, 1],
            "incident_real": eta_incident.real,
            "incident_imag": eta_incident.imag,
            "incident_abs": np.abs(eta_incident),
            "diffracted_real": eta_diffracted.real,
            "diffracted_imag": eta_diffracted.imag,
            "diffracted_abs": np.abs(eta_diffracted),
            "total_real": eta_total.real,
            "total_imag": eta_total.imag,
            "total_abs": np.abs(eta_total),
        }
    )


def plot_total_elevation_field(field_df, grid_x, grid_y, n, period, output_path):
    """Save a signed real-part total free-surface contour plot."""
    import matplotlib.pyplot as plt

    eta = field_df["total_real"].to_numpy().reshape(grid_x.shape)
    finite_eta = eta[np.isfinite(eta)]
    if finite_eta.size == 0:
        raise ValueError("No finite total_real values are available for field plotting.")

    color_limit = float(np.nanmax(np.abs(finite_eta)))
    if color_limit == 0.0:
        color_limit = 1.0

    fig, ax = plt.subplots(figsize=(7.0, 4.8), constrained_layout=True)
    contour_levels = np.linspace(-color_limit, color_limit, 41)
    contour = ax.contourf(
        grid_x,
        grid_y,
        eta,
        levels=contour_levels,
        cmap="RdBu_r",
    )
    centers = np.asarray(cylinder_centers(n), dtype=float)
    ax.scatter(
        centers[:, 0],
        centers[:, 1],
        s=30,
        c="black",
        marker="o",
        label="Cylinder centres",
    )
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("x coordinate (m)")
    ax.set_ylabel("y coordinate (m)")
    ax.set_title(f"Signed total free-surface elevation, N={n}, T={period:.2f} s")
    cbar = fig.colorbar(contour, ax=ax)
    cbar.set_label("Re(total eta), unit incident-wave amplitude")
    ax.legend(loc="upper right")
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def run_field_plot_workflow(
    n=FIELD_PLOT_DEFAULT_ARRAY_SIZE,
    period=FIELD_PLOT_DEFAULT_PERIOD,
    grid_shape=FIELD_PLOT_DEFAULT_GRID_SHAPE,
):
    """Run a selected-period 2D free-surface field-plot workflow.

    This workflow is independent from diagnostics, scan-segment, and
    merge-segments. It performs one fixed-body diffraction solve for the chosen
    array size and period, writes the selected-period field grid to ``outputs/``,
    and saves a signed real-part contour plot to ``figures/``.
    """
    ensure_output_dirs()
    x, y, grid_x, grid_y, points = field_plot_grid(grid_shape=grid_shape)

    solver, problem, result, mesh_level = solve_fixed_body_diffraction_case(
        n=n,
        period=period,
        resolution=FORMAL_MESH_RESOLUTION,
        mesh_level=FORMAL_MESH_LEVEL,
    )
    field_df = free_surface_field_dataframe(solver, result, problem, points)
    field_df = field_df.assign(
        array_size=n,
        period=period,
        mesh_level=mesh_level,
        grid_nx=len(x),
        grid_ny=len(y),
    )

    output_stem = f"field_N{n}_T{period:.2f}".replace(".", "p")
    csv_path = os.path.join(OUTPUT_DIR, f"{output_stem}.csv")
    png_path = os.path.join(FIGURE_DIR, f"{output_stem}.png")
    field_df.to_csv(csv_path, index=False)
    plot_total_elevation_field(field_df, grid_x, grid_y, n, period, png_path)

    print(
        "Finished fixed-body diffraction field plot: "
        f"N={n}, T={period:.2f} s, grid={len(x)}x{len(y)}"
    )
    print(f"Saved field grid: {csv_path}")
    print(f"Saved field figure: {png_path}")
    return csv_path, png_path

def run_probe_smoke_test(n=4, period=SMOKE_TEST_PERIOD):
    """Run one fixed-body diffraction case and save free-surface probes."""
    ensure_output_dirs()

    solver, problem, result, _ = solve_fixed_body_diffraction_case(
        n=n,
        period=period,
        resolution=FORMAL_MESH_RESOLUTION,
        mesh_level=FORMAL_MESH_LEVEL,
    )
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


def run_probe_field_consistency_check(n=6, period=1.00, grid_shape=(41, 31)):
    """Compare P0 values from probe and field-grid workflows for one case."""
    _, _, _, _, points = field_plot_grid(grid_shape=grid_shape)
    p0_point = np.array([[0.0, 0.0]], dtype=float)
    if not np.any(np.all(np.isclose(points, p0_point), axis=1)):
        raise ValueError("Grid does not include P0=(0, 0); choose odd nx and ny.")

    solver, problem, result, mesh_level = solve_fixed_body_diffraction_case(
        n=n,
        period=period,
        resolution=FORMAL_MESH_RESOLUTION,
        mesh_level=FORMAL_MESH_LEVEL,
    )
    probe_p0 = point_probe_dataframe(solver, result, problem).set_index("probe").loc["P0"]
    field_p0 = free_surface_field_dataframe(solver, result, problem, p0_point).iloc[0]

    total_abs_probe = float(probe_p0["total_abs"])
    total_abs_field = float(field_p0["total_abs"])
    relative_diff = abs(total_abs_probe - total_abs_field) / abs(total_abs_probe)

    consistency_df = pd.DataFrame(
        [
            {
                "array_size": n,
                "period": period,
                "mesh_level": mesh_level,
                "probe_P0_total_abs": total_abs_probe,
                "field_P0_total_abs": total_abs_field,
                "probe_P0_diffracted_abs": float(probe_p0["diffracted_abs"]),
                "field_P0_diffracted_abs": float(field_p0["diffracted_abs"]),
                "relative_diff_total_abs": relative_diff,
            }
        ]
    )
    output_stem = f"consistency_probe_field_N{n}_T{period:.2f}".replace(".", "p")
    output_path = os.path.join(OUTPUT_DIR, f"{output_stem}.csv")
    consistency_df.to_csv(output_path, index=False)
    print(f"Saved probe/field consistency check: {output_path}")
    return output_path


def run_all_smoke_tests():
    """Run small fixed-body diffraction smoke tests for all array sizes."""
    output_paths = []
    for n in SMOKE_TEST_ARRAY_SIZES:
        output_paths.append(run_probe_smoke_test(n=n, period=SMOKE_TEST_PERIOD))
    return output_paths


def parse_args():
    """Parse command-line arguments for local scan workflows."""
    parser = argparse.ArgumentParser(
        description="Run fixed-body diffraction diagnostics, scan, and field-plot workflows."
    )
    parser.add_argument(
        "--mode",
        choices=("diagnostics", "scan-segment", "merge-segments", "field-plot"),
        default="diagnostics",
        help="Workflow to run. The default diagnostics mode does not run a period scan.",
    )
    parser.add_argument(
        "--start",
        type=float,
        help="Inclusive segment start period in seconds for --mode scan-segment.",
    )
    parser.add_argument(
        "--end",
        type=float,
        help="Inclusive segment end period in seconds for --mode scan-segment.",
    )
    parser.add_argument(
        "--step",
        type=float,
        default=N8_SCAN_STEP,
        help="Period step in seconds for --mode scan-segment (default: 0.01).",
    )
    parser.add_argument(
        "--scan-n",
        type=int,
        choices=(4, 6, 8),
        default=N8_SCAN_ARRAY_SIZE,
        help="Array size for --mode scan-segment and --mode merge-segments (default: 8).",
    )
    parser.add_argument(
        "--field-n",
        type=int,
        default=FIELD_PLOT_DEFAULT_ARRAY_SIZE,
        help="Array size for --mode field-plot (default: 4).",
    )
    parser.add_argument(
        "--field-period",
        type=float,
        default=FIELD_PLOT_DEFAULT_PERIOD,
        help="Selected period in seconds for --mode field-plot (default: 1.00).",
    )
    parser.add_argument(
        "--field-nx",
        type=int,
        default=FIELD_PLOT_DEFAULT_GRID_SHAPE[0],
        help="Number of x samples for --mode field-plot (default: 121).",
    )
    parser.add_argument(
        "--field-ny",
        type=int,
        default=FIELD_PLOT_DEFAULT_GRID_SHAPE[1],
        help="Number of y samples for --mode field-plot (default: 81).",
    )
    parser.add_argument(
        "--field-quantity",
        choices=("abs",),
        default="abs",
        help="Field quantity placeholder for compatibility (currently only: abs).",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if args.mode == "diagnostics":
        save_mesh_diagnostics_N8()
        return

    if args.mode == "scan-segment":
        if args.start is None or args.end is None:
            raise ValueError("--mode scan-segment requires both --start and --end.")
        run_period_scan_segment(args.scan_n, args.start, args.end, step=args.step)
        return

    if args.mode == "merge-segments":
        merge_period_scan_segments(args.scan_n)
        return

    if args.mode == "field-plot":
        run_field_plot_workflow(
            n=args.field_n,
            period=args.field_period,
            grid_shape=(args.field_nx, args.field_ny),
        )
        return

    raise ValueError(f"Unsupported mode: {args.mode}")


if __name__ == "__main__":
    main()
