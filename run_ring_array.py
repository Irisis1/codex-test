import os

import numpy as np
import pandas as pd

import capytaine as cpt
from capytaine.bem.airy_waves import airy_waves_free_surface_elevation
from capytaine.green_functions.abstract_green_function import GreenFunctionEvaluationError


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
    """Return main and cross line probes for smoke-test sampling."""
    main_x = np.linspace(-1.5, 1.5, 21)
    cross_y = np.linspace(-1.0, 1.0, 21)

    main_line = [("main_line_y0p2", i, x, 0.2) for i, x in enumerate(main_x)]
    cross_line = [("cross_line_x0p0", i, 0.0, y) for i, y in enumerate(cross_y)]
    return main_line + cross_line


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
