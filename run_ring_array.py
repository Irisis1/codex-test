import os

import numpy as np
import pandas as pd

try:
    import capytaine as cpt
    from capytaine.bem.airy_waves import airy_waves_free_surface_elevation
except ImportError as exc:
    raise ImportError(
        "Capytaine is not installed. Install dependencies with "
        "`pip install -r requirements.txt` or use `environment.yml`."
    ) from exc


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
PROBES = (
    ("P0", 0.0, 0.0),
    ("P1", 0.1, 0.0),
    ("P2", -0.1, 0.0),
    ("P3", 0.0, 0.1),
    ("P4", 0.0, -0.1),
    ("front", -2.0, 0.0),
    ("rear", 2.0, 0.0),
)


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


def free_surface_probe_dataframe(solver, result, problem, n, period):
    """Compute incident, diffraction, and total free-surface elevation probes.

    The body has no degrees of freedom, so the solved ``DiffractionProblem`` is
    fixed-body diffraction only. Capytaine's BEM post-processing returns the
    scattered/diffracted elevation from the solved source distribution; the
    undisturbed Airy-wave elevation is added to report the physical total
    elevation for Capytaine's unit incident-wave amplitude normalization.
    """
    labels = [probe[0] for probe in PROBES]
    points = np.array([(probe[1], probe[2]) for probe in PROBES], dtype=float)

    eta_diffraction = np.asarray(
        solver.compute_free_surface_elevation(points, result), dtype=complex
    )
    eta_incident = np.asarray(
        airy_waves_free_surface_elevation(points, problem), dtype=complex
    )
    eta_total = eta_incident + eta_diffraction

    records = []
    for label, (x, y), eta_i, eta_d, eta in zip(
        labels, points, eta_incident, eta_diffraction, eta_total
    ):
        records.append(
            {
                "N": n,
                "period_s": period,
                "omega_rad_s": problem.omega,
                "probe": label,
                "x_m": x,
                "y_m": y,
                "eta_real": eta.real,
                "eta_imag": eta.imag,
                "eta_abs": abs(eta),
                "eta_incident_real": eta_i.real,
                "eta_incident_imag": eta_i.imag,
                "eta_incident_abs": abs(eta_i),
                "eta_diffraction_real": eta_d.real,
                "eta_diffraction_imag": eta_d.imag,
                "eta_diffraction_abs": abs(eta_d),
            }
        )

    return pd.DataFrame(records)


def run_probe_smoke_test(n=4, period=1.00):
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
    df = free_surface_probe_dataframe(solver, result, problem, n, period)

    output_stem = f"probe_smoke_test_N{n}_T{period:.2f}".replace(".", "p")
    csv_path = os.path.join(OUTPUT_DIR, f"{output_stem}.csv")
    df.to_csv(csv_path, index=False)

    print(
        f"Finished fixed-body diffraction probe smoke test: "
        f"N={n}, T={period:.2f} s"
    )
    print(f"Saved: {csv_path}")


def main():
    run_probe_smoke_test(n=4, period=1.00)


if __name__ == "__main__":
    main()
