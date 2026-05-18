"""Plot N=8 mesh-convergence figures from existing post-processing CSV files.

This script intentionally performs plotting and tabular post-processing only. It
reads the completed N=8 representative-period mesh-convergence CSV files already
present in outputs/, writes figures and a compact summary table, and does not
instantiate or run any Capytaine BEM solver.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

OUTPUT_DIR = Path("outputs")
FIGURE_DIR = Path("figures")

CONVERGENCE_CSV = OUTPUT_DIR / "mesh_convergence_N8_representative_periods.csv"
MESH_DIAGNOSTICS_CSV = OUTPUT_DIR / "mesh_diagnostics_N8.csv"
SUMMARY_CSV = OUTPUT_DIR / "N8_mesh_convergence_summary.csv"

ERROR_FIGURE_STEM = FIGURE_DIR / "N8_mesh_convergence_errors"
VALUES_FIGURE_STEM = FIGURE_DIR / "N8_mesh_convergence_values"

DPI = 300
REPRESENTATIVE_PERIODS = [0.98, 1.00, 1.02, 1.36, 1.38, 1.40]
MESH_LEVEL_ORDER = ["coarse", "base", "medium", "fine"]
ERROR_MESH_LEVELS = ["coarse", "base", "medium"]
ERROR_THRESHOLD_PERCENT = 2.0

CONVERGENCE_REQUIRED_COLUMNS = [
    "period",
    "mesh_level",
    "cylinder_resolution",
    "total_vertices",
    "total_faces",
    "center_mean_abs",
    "center_max_abs",
    "S_rear_front",
    "error_center_mean_percent",
    "error_center_max_percent",
    "error_S_percent",
]

NUMERIC_COLUMNS = [
    "period",
    "total_vertices",
    "total_faces",
    "center_mean_abs",
    "center_max_abs",
    "S_rear_front",
    "error_center_mean_percent",
    "error_center_max_percent",
    "error_S_percent",
]

ERROR_PANELS = [
    ("error_center_mean_percent", "(a) Center mean response"),
    ("error_center_max_percent", "(b) Center max response"),
    ("error_S_percent", "(c) Transmission-like indicator"),
]

VALUE_PANELS = [
    ("center_mean_abs", "(a) Center mean response"),
    ("center_max_abs", "(b) Center max response"),
    ("S_rear_front", "(c) Transmission-like indicator"),
]

STYLE_BY_LEVEL = {
    "coarse": {"color": "tab:blue", "marker": "o", "linestyle": "-"},
    "base": {"color": "tab:orange", "marker": "s", "linestyle": "-"},
    "medium": {"color": "tab:green", "marker": "^", "linestyle": "-"},
    "fine": {"color": "tab:red", "marker": "D", "linestyle": "-"},
}


def ensure_dirs() -> None:
    """Create output directories for figures and derived tables."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    FIGURE_DIR.mkdir(exist_ok=True)


def require_columns(dataframe: pd.DataFrame, required_columns: list[str], source: Path | str) -> None:
    """Raise a clear error if a dataframe is missing required columns."""
    missing_columns = [column for column in required_columns if column not in dataframe.columns]
    if missing_columns:
        missing_text = ", ".join(missing_columns)
        raise ValueError(f"{source} is missing required column(s): {missing_text}")


def read_inputs() -> tuple[pd.DataFrame, pd.DataFrame | None]:
    """Read and validate existing N=8 mesh-convergence input CSV files."""
    if not CONVERGENCE_CSV.exists():
        raise FileNotFoundError(
            "Missing required hydrodynamic mesh-convergence input CSV: "
            f"{CONVERGENCE_CSV}. This plotting script only reads existing outputs "
            "and will not run the Capytaine BEM solver to regenerate it."
        )

    conv_df = pd.read_csv(CONVERGENCE_CSV)
    require_columns(conv_df, CONVERGENCE_REQUIRED_COLUMNS, CONVERGENCE_CSV)
    conv_df = conv_df.copy()
    for column in NUMERIC_COLUMNS:
        conv_df[column] = pd.to_numeric(conv_df[column], errors="coerce")

    if conv_df[NUMERIC_COLUMNS].isna().any().any():
        bad_columns = conv_df[NUMERIC_COLUMNS].columns[conv_df[NUMERIC_COLUMNS].isna().any()].tolist()
        raise ValueError(
            f"{CONVERGENCE_CSV} contains non-numeric or NaN values in required numeric column(s): "
            f"{', '.join(bad_columns)}"
        )
    if not np.isfinite(conv_df[NUMERIC_COLUMNS].to_numpy(dtype=float)).all():
        raise ValueError(f"{CONVERGENCE_CSV} contains non-finite values in required numeric columns.")

    conv_df["period"] = conv_df["period"].round(2)
    conv_df["mesh_level"] = conv_df["mesh_level"].astype(str)
    conv_df["cylinder_resolution"] = conv_df["cylinder_resolution"].astype(str)

    mesh_diag_df: pd.DataFrame | None = None
    if MESH_DIAGNOSTICS_CSV.exists():
        mesh_diag_df = pd.read_csv(MESH_DIAGNOSTICS_CSV)
        if "mesh_level" not in mesh_diag_df.columns:
            print(
                f"Warning: {MESH_DIAGNOSTICS_CSV} exists but has no mesh_level column; "
                "summary geometry fields will use the convergence CSV only."
            )
            mesh_diag_df = None
        else:
            mesh_diag_df = mesh_diag_df.copy()
            mesh_diag_df["mesh_level"] = mesh_diag_df["mesh_level"].astype(str)
            for column in ["total_vertices", "total_faces"]:
                if column in mesh_diag_df.columns:
                    mesh_diag_df[column] = pd.to_numeric(mesh_diag_df[column], errors="coerce")
    else:
        print(
            f"Warning: optional geometry diagnostics file {MESH_DIAGNOSTICS_CSV} was not found; "
            "summary will be generated from mesh-convergence data only."
        )

    return conv_df, mesh_diag_df


def ordered_mesh_levels(levels: pd.Series) -> list[str]:
    """Return mesh levels in the expected order, appending any unexpected names."""
    unique_levels = list(dict.fromkeys(levels.astype(str)))
    known_levels = [level for level in MESH_LEVEL_ORDER if level in unique_levels]
    extra_levels = sorted(level for level in unique_levels if level not in MESH_LEVEL_ORDER)
    return known_levels + extra_levels


def first_non_null_text(series: pd.Series) -> str:
    """Return the first non-empty string in a series, or an empty string."""
    for value in series.dropna():
        text = str(value)
        if text:
            return text
    return ""


def build_summary_table(conv_df: pd.DataFrame, mesh_diag_df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Build the formal N=8 mesh-convergence summary table."""
    require_columns(conv_df, CONVERGENCE_REQUIRED_COLUMNS, "conv_df")

    rows: list[dict[str, object]] = []
    for mesh_level in ordered_mesh_levels(conv_df["mesh_level"]):
        subset = conv_df.loc[conv_df["mesh_level"] == mesh_level].copy()
        row: dict[str, object] = {
            "mesh_level": mesh_level,
            "cylinder_resolution": first_non_null_text(subset["cylinder_resolution"]),
            "mean_total_faces": float(subset["total_faces"].mean()),
            "mean_total_vertices": float(subset["total_vertices"].mean()),
            "max_error_center_mean_percent": float(subset["error_center_mean_percent"].max()),
            "max_error_center_max_percent": float(subset["error_center_max_percent"].max()),
            "max_error_S_percent": float(subset["error_S_percent"].max()),
        }

        if mesh_diag_df is not None:
            diag_subset = mesh_diag_df.loc[mesh_diag_df["mesh_level"] == mesh_level]
            if not diag_subset.empty:
                if "cylinder_resolution" in diag_subset.columns:
                    row["cylinder_resolution"] = first_non_null_text(diag_subset["cylinder_resolution"]) or row[
                        "cylinder_resolution"
                    ]
                if "total_faces" in diag_subset.columns and diag_subset["total_faces"].notna().any():
                    row["mean_total_faces"] = float(diag_subset["total_faces"].mean())
                if "total_vertices" in diag_subset.columns and diag_subset["total_vertices"].notna().any():
                    row["mean_total_vertices"] = float(diag_subset["total_vertices"].mean())

        is_selected = mesh_level == "medium"
        row["selected_for_formal_scan"] = "yes" if is_selected else "no"
        if is_selected:
            max_errors = [
                row["max_error_center_mean_percent"],
                row["max_error_center_max_percent"],
                row["max_error_S_percent"],
            ]
            if all(float(error) < ERROR_THRESHOLD_PERCENT for error in max_errors):
                row["selection_reason"] = "deviations below 2% for all representative periods and key indicators"
            else:
                row["selection_reason"] = (
                    "selected for formal scan, but at least one representative-period key-indicator "
                    "deviation is not below 2%"
                )
        else:
            row["selection_reason"] = "not selected; medium mesh is the formal-scan mesh level"
        rows.append(row)

    summary_df = pd.DataFrame(rows)
    numeric_columns = [
        "mean_total_faces",
        "mean_total_vertices",
        "max_error_center_mean_percent",
        "max_error_center_max_percent",
        "max_error_S_percent",
    ]
    summary_df[numeric_columns] = summary_df[numeric_columns].round(6)
    return summary_df


def format_period_axis(ax: plt.Axes) -> None:
    """Apply common representative-period axis formatting."""
    ax.set_xlabel("period (s)")
    ax.set_xticks(REPRESENTATIVE_PERIODS)
    ax.set_xticklabels([f"{period:.2f}" for period in REPRESENTATIVE_PERIODS], rotation=35, ha="right")
    ax.grid(True, alpha=0.28, linewidth=0.7)


def save_figure(fig: plt.Figure, stem: Path) -> None:
    """Save matching PNG and PDF versions of a figure."""
    fig.savefig(stem.with_suffix(".png"), dpi=DPI, bbox_inches="tight")
    fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)


def plot_mesh_convergence_errors(conv_df: pd.DataFrame) -> None:
    """Plot relative errors against the fine mesh at representative periods."""
    fig, axes = plt.subplots(1, 3, figsize=(12.0, 4.2), constrained_layout=True, sharex=True)
    fig.suptitle("N=8 mesh-convergence errors at representative periods")

    for ax, (metric, title) in zip(axes, ERROR_PANELS, strict=True):
        for mesh_level in ERROR_MESH_LEVELS:
            subset = conv_df.loc[conv_df["mesh_level"] == mesh_level].sort_values("period")
            if subset.empty:
                continue
            ax.plot(
                subset["period"],
                subset[metric],
                linewidth=1.6,
                markersize=4.5,
                label=mesh_level,
                **STYLE_BY_LEVEL.get(mesh_level, {}),
            )
        ax.axhline(
            ERROR_THRESHOLD_PERCENT,
            color="0.25",
            linestyle="--",
            linewidth=1.1,
            label="2% threshold",
        )
        ax.set_title(title)
        ax.set_ylabel("Relative error against fine mesh (%)")
        format_period_axis(ax)
        ax.legend(fontsize=8.5)

    save_figure(fig, ERROR_FIGURE_STEM)


def plot_mesh_convergence_values(conv_df: pd.DataFrame) -> None:
    """Plot absolute response indicators for all available mesh levels."""
    fig, axes = plt.subplots(1, 3, figsize=(12.0, 4.2), constrained_layout=True, sharex=True)
    fig.suptitle("N=8 mesh-convergence values at representative periods")

    for ax, (metric, title) in zip(axes, VALUE_PANELS, strict=True):
        for mesh_level in ordered_mesh_levels(conv_df["mesh_level"]):
            subset = conv_df.loc[conv_df["mesh_level"] == mesh_level].sort_values("period")
            if subset.empty:
                continue
            ax.plot(
                subset["period"],
                subset[metric],
                linewidth=1.6,
                markersize=4.5,
                label=mesh_level,
                **STYLE_BY_LEVEL.get(mesh_level, {}),
            )
        ax.set_title(title)
        ax.set_ylabel(metric)
        format_period_axis(ax)
        ax.legend(fontsize=8.5)

    save_figure(fig, VALUES_FIGURE_STEM)


def main() -> None:
    """Run N=8 mesh-convergence plotting and summary generation."""
    ensure_dirs()
    conv_df, mesh_diag_df = read_inputs()
    summary_df = build_summary_table(conv_df, mesh_diag_df)
    summary_df.to_csv(SUMMARY_CSV, index=False)
    plot_mesh_convergence_errors(conv_df)
    plot_mesh_convergence_values(conv_df)

    print(f"Wrote {ERROR_FIGURE_STEM.with_suffix('.png')}")
    print(f"Wrote {ERROR_FIGURE_STEM.with_suffix('.pdf')}")
    print(f"Wrote {VALUES_FIGURE_STEM.with_suffix('.png')}")
    print(f"Wrote {VALUES_FIGURE_STEM.with_suffix('.pdf')}")
    print(f"Wrote {SUMMARY_CSV}")

    medium = summary_df.loc[summary_df["mesh_level"] == "medium"]
    if not medium.empty:
        max_errors = medium[
            [
                "max_error_center_mean_percent",
                "max_error_center_max_percent",
                "max_error_S_percent",
            ]
        ].iloc[0]
        below_threshold = bool((max_errors < ERROR_THRESHOLD_PERCENT).all())
        print(
            "Medium mesh maximum errors below 2%: "
            f"{'yes' if below_threshold else 'no'} "
            f"({max_errors.to_dict()})"
        )


if __name__ == "__main__":
    main()
