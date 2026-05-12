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


def make_fixed_cylinder(x, y):
    """Create one fixed vertical circular cylinder."""
    mesh = cpt.mesh_vertical_cylinder(
        radius=CYLINDER_RADIUS,
        length=CYLINDER_DRAFT,
        center=(x, y, -CYLINDER_DRAFT / 2.0),
        resolution=(12, 12, 4),
    )

    body = cpt.FloatingBody(mesh=mesh)
    body.keep_immersed_part()
    return body


def make_ring_array(n):
    """Create a fixed n-cylinder ring array."""
    bodies = []

    for i, (x, y) in enumerate(cylinder_centers(n)):
        body = make_fixed_cylinder(x, y)
        body.name = f"cylinder_{i + 1}"
        bodies.append(body)

    array_body = bodies[0]
    for body in bodies[1:]:
        array_body = array_body + body

    array_body.name = f"ring_{n}_cylinders"
    return array_body


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


def main():
    run_all_smoke_tests()


if __name__ == "__main__":
    main()
