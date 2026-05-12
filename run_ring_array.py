import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

try:
    import capytaine as cpt
except ImportError as exc:
    raise ImportError(
        "Capytaine is not installed. Install dependencies with "
        "`pip install -r requirements.txt` or use `environment.yml`."
    ) from exc


OUTPUT_DIR = "outputs"
FIGURE_DIR = "figures"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(FIGURE_DIR, exist_ok=True)


# Physical parameters
G = 9.81
RHO = 1000.0
WATER_DEPTH = 0.60

CYLINDER_RADIUS = 0.06
CYLINDER_DRAFT = 0.598
RING_RADIUS = 0.30


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


def run_smoke_test(n=4, periods=(1.00,)):
    """Run a small Capytaine smoke test."""
    body = make_ring_array(n)
    solver = cpt.BEMSolver()

    records = []

    for period in periods:
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

        records.append(
            {
                "N": n,
                "period_s": period,
                "omega_rad_s": omega,
                "force_abs_sum": float(np.sum(np.abs(result.forces.values))),
            }
        )

        print(f"Finished: N={n}, T={period:.2f} s")

    df = pd.DataFrame(records)
    csv_path = os.path.join(OUTPUT_DIR, f"smoke_test_N{n}.csv")
    df.to_csv(csv_path, index=False)

    plt.figure(figsize=(6, 4))
    plt.plot(df["period_s"], df["force_abs_sum"], marker="o")
    plt.xlabel("Wave period T (s)")
    plt.ylabel("Sum of absolute diffraction force")
    plt.tight_layout()

    fig_path = os.path.join(FIGURE_DIR, f"smoke_test_N{n}.png")
    plt.savefig(fig_path, dpi=300)
    plt.close()

    print(f"Saved: {csv_path}")
    print(f"Saved: {fig_path}")


def main():
    run_smoke_test(n=4, periods=(1.00,))


if __name__ == "__main__":
    main()
