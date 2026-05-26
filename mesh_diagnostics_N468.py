import os

import pandas as pd

from run_ring_array import MESH_LEVEL_RESOLUTIONS, OUTPUT_DIR, ensure_output_dirs, make_ring_array


TARGET_ARRAY_SIZES = (4, 6, 8)
TARGET_MESH_LEVEL = "medium"


def build_n468_mesh_diagnostics_dataframe():
    """Build medium-mesh diagnostics for N=4/6/8 without solving BEM problems."""
    if TARGET_MESH_LEVEL not in MESH_LEVEL_RESOLUTIONS:
        raise KeyError(f"Mesh level '{TARGET_MESH_LEVEL}' is not defined in run_ring_array.py")

    nr, ntheta, nz = MESH_LEVEL_RESOLUTIONS[TARGET_MESH_LEVEL]
    records = []

    for array_size in TARGET_ARRAY_SIZES:
        body = make_ring_array(array_size, resolution=(nr, ntheta, nz))
        mesh = body.mesh
        estimated_faces_per_cylinder = int(mesh.nb_faces // array_size)
        actual_faces_per_cylinder = (
            float(mesh.nb_faces) / float(array_size) if mesh.nb_faces % array_size == 0 else "not_integer"
        )

        records.append(
            {
                "array_size": array_size,
                "mesh_level": TARGET_MESH_LEVEL,
                "nr": nr,
                "ntheta": ntheta,
                "nz": nz,
                "number_of_cylinders": array_size,
                "nb_faces": int(mesh.nb_faces),
                "nb_vertices": int(mesh.nb_vertices),
                "estimated_faces_per_cylinder": estimated_faces_per_cylinder,
                "actual_faces_per_cylinder_if_applicable": actual_faces_per_cylinder,
            }
        )

    return pd.DataFrame(records)


def main():
    ensure_output_dirs()
    diagnostics_df = build_n468_mesh_diagnostics_dataframe()
    output_path = os.path.join(OUTPUT_DIR, "N468_mesh_diagnostics.csv")
    diagnostics_df.to_csv(output_path, index=False)
    print(f"Saved: {output_path}")
    print(diagnostics_df.to_csv(index=False))


if __name__ == "__main__":
    main()
