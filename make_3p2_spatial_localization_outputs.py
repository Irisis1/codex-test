"""Create Section 3.2 spatial-localization text and table outputs.

This is a lightweight post-processing script only. It does not import or run
Capytaine, does not modify any source CSV files, and generates the paper figures from
existing refined-scan CSV outputs plus the fixed Section 3.2 peak-comparison
values. The numerical values are the already identified refined-scan
central-response peak values used for the Section 3.2 localization discussion.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUTPUT_DIR = Path("outputs")
FIGURE_DIR = Path("figures")
DRAFT_PATH = OUTPUT_DIR / "Results_3p2_spatial_localization_draft.md"
TABLE_PATH = OUTPUT_DIR / "N468_3p2_spatial_localization_table_for_paper.csv"
RLOC_FIGURE_PATH = FIGURE_DIR / "N468_Rloc_refined_0p85_1p05_paper_combined.png"
PEAK_VALUE_FIGURE_PATH = (
    FIGURE_DIR / "N468_center_probe_peak_value_comparison_paper.png"
)
PEAK_PERIOD_FIGURE_PATH = (
    FIGURE_DIR / "N468_center_probe_peak_period_comparison_paper.png"
)
REFINED_COMBINED_PATH = OUTPUT_DIR / "N468_refined_center_peak_table_0p85_1p05.csv"
REFINED_SUMMARY_PATHS = {
    4: OUTPUT_DIR / "N4_refined_period_scan_summary_0p85_1p05.csv",
    6: OUTPUT_DIR / "N6_refined_period_scan_summary_0p85_1p05.csv",
    8: OUTPUT_DIR / "N8_refined_period_scan_summary_0p85_1p05.csv",
}
PERIOD_RANGE = (0.85, 1.05)
LOWER_BOUNDARY_INTERVAL = (0.85, 0.87)


@dataclass(frozen=True)
class SpatialLocalizationRecord:
    """One row of Section 3.2 spatial-localization summary data."""

    array_size: int
    mean_peak_period_s: float
    mean_peak_amplitude: float
    max_peak_period_s: float
    max_peak_amplitude: float

    @property
    def localization_ratio(self) -> float:
        """Return peak local-to-mean central amplification ratio."""
        return self.max_peak_amplitude / self.mean_peak_amplitude

    @property
    def peak_period_offset_s(self) -> float:
        """Return local-maximum peak period minus mean-response peak period."""
        return self.max_peak_period_s - self.mean_peak_period_s


RECORDS: tuple[SpatialLocalizationRecord, ...] = (
    SpatialLocalizationRecord(4, 0.955, 1.139445, 0.870, 1.184359),
    SpatialLocalizationRecord(6, 0.970, 1.238387, 0.905, 1.285190),
    SpatialLocalizationRecord(8, 0.995, 1.355463, 0.945, 1.418618),
)


def ensure_output_dir() -> None:
    """Create the outputs and figures directories if needed."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    FIGURE_DIR.mkdir(exist_ok=True)


def write_table(records: tuple[SpatialLocalizationRecord, ...]) -> None:
    """Write the compact Section 3.2 table used by the paper draft."""
    fieldnames = [
        "array_size",
        "A_c_mean_peak_period_s",
        "A_c_mean_peak",
        "A_c_max_peak_period_s",
        "A_c_max_peak",
        "R_loc_peak_max_over_mean",
        "peak_period_offset_max_minus_mean_s",
    ]
    with TABLE_PATH.open("w", newline="", encoding="utf-8") as table_file:
        writer = csv.DictWriter(table_file, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    "array_size": record.array_size,
                    "A_c_mean_peak_period_s": f"{record.mean_peak_period_s:.3f}",
                    "A_c_mean_peak": f"{record.mean_peak_amplitude:.6f}",
                    "A_c_max_peak_period_s": f"{record.max_peak_period_s:.3f}",
                    "A_c_max_peak": f"{record.max_peak_amplitude:.6f}",
                    "R_loc_peak_max_over_mean": f"{record.localization_ratio:.6f}",
                    "peak_period_offset_max_minus_mean_s": f"{record.peak_period_offset_s:.3f}",
                }
            )


def markdown_table(records: tuple[SpatialLocalizationRecord, ...]) -> str:
    """Return a Markdown version of the Section 3.2 localization table."""
    lines = [
        "| N | Peak $A_{c,\\mathrm{mean}}$ | T for mean peak (s) | "
        "Peak $A_{c,\\max}$ | T for max peak (s) | $R_{loc}$ | "
        "$T(A_{c,\\max})-T(A_{c,\\mathrm{mean}})$ (s) |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for record in records:
        lines.append(
            f"| {record.array_size} | {record.mean_peak_amplitude:.6f} | "
            f"{record.mean_peak_period_s:.3f} | {record.max_peak_amplitude:.6f} | "
            f"{record.max_peak_period_s:.3f} | {record.localization_ratio:.6f} | "
            f"{record.peak_period_offset_s:.3f} |"
        )
    return "\n".join(lines)


def write_draft(records: tuple[SpatialLocalizationRecord, ...] = RECORDS) -> None:
    """Write the Section 3.2 Results draft without changing Method or Section 3.1."""
    table_text = markdown_table(records)
    draft = f"""# 3.2 Spatial localization of the central response

The spatial localization of the central response was evaluated by comparing the
maximum response among the five predefined centre probes with the corresponding
mean-response indicator for the same fixed circular-cylinder ring arrays. The
analysis uses the same incident-amplitude-normalized frequency-domain response
amplitudes and the same probe definitions as Section 3.1. No additional
Capytaine calculations, physical-parameter changes, or normalization changes are
introduced here.

For each array size, the local central indicator is summarized by
\\(R_{{loc}} = A_{{c,\\max}}^{{peak}} / A_{{c,\\mathrm{{mean}}}}^{{peak}}\\), where the two
peak amplitudes are taken from the refined short-period results used in the
central-response discussion. This ratio is not a transmission coefficient and is
not used as evidence for a modal or resonance mechanism; it is only a compact
measure of how much the strongest centre probe exceeds the five-probe central
mean at their respective refined-scan peak values.

{table_text}

The three arrays show only moderate local-to-mean separation in the refined
short-period interval. The localization ratio is 1.039417 for N=4, 1.037794 for
N=6, and 1.046593 for N=8. Thus, although the absolute central-response peaks
increase with array size, the strongest central probe exceeds the five-probe mean
by only about four to five percent in all three cases. This supports the more
limited interpretation that the selected centre probes experience a localized
maximum superposed on a broader central amplification pattern, rather than a
strongly isolated single-probe response.

The peak periods of \\(A_{{c,\\max}}\\) occur earlier than the peak periods of
\\(A_{{c,\\mathrm{{mean}}}}\\) for all three arrays. The offsets
\\(T(A_{{c,\\max}})-T(A_{{c,\\mathrm{{mean}}}})\\) are -0.085 s for N=4, -0.065 s for
N=6, and -0.050 s for N=8. The decreasing magnitude of this offset with
increasing array size suggests that the local maximum and the spatially averaged
central response become more closely aligned in period for the denser ring
arrays. The N=4 local-maximum peak remains close to the lower end of the refined
inspection interval and should therefore be interpreted cautiously, consistent
with the Section 3.1 discussion.

Overall, Section 3.2 indicates that increasing N strengthens both the mean and
local-maximum central responses while preserving a relatively small local-to-mean
contrast across the five centre probes. The result should be described as a
frequency-dependent spatial localization trend for the specified fixed-body
diffraction problem, not as confirmation of resonance, cloaking, or a
transmission-coefficient effect.
"""
    DRAFT_PATH.write_text(draft, encoding="utf-8")


def _first_existing_value(row: dict[str, str], names: tuple[str, ...]) -> str | None:
    """Return the first non-empty CSV value among possible column names."""
    for name in names:
        value = row.get(name)
        if value not in (None, ""):
            return value
    return None


def _float_from_row(row: dict[str, str], names: tuple[str, ...]) -> float | None:
    """Return a float from the first matching CSV column, if possible."""
    value = _first_existing_value(row, names)
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _read_rloc_curve(
    path: Path, array_size: int | None = None
) -> list[tuple[float, float]]:
    """Read an R_loc curve from a refined-scan CSV without modifying the file.

    R_loc is defined as A_c,max / A_c,mean. If the source CSV already contains
    center_max_to_mean_ratio, that column is used directly. Otherwise, the ratio
    is computed only when both center_max_abs and center_mean_abs are present.
    """
    if not path.exists():
        print(f"Missing refined-scan CSV for R_loc curve: {path}")
        return []

    points: list[tuple[float, float]] = []
    with path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        fieldnames = set(reader.fieldnames or [])
        has_direct_ratio = "center_max_to_mean_ratio" in fieldnames
        has_ratio_inputs = {"center_max_abs", "center_mean_abs"}.issubset(fieldnames)
        if not has_direct_ratio and not has_ratio_inputs:
            print(
                "Missing R_loc fields in "
                f"{path}: need center_max_to_mean_ratio or both "
                "center_max_abs and center_mean_abs."
            )
            return []

        for row in reader:
            if array_size is not None:
                row_array_size = _float_from_row(
                    row,
                    ("array_size", "N", "n_cylinders", "num_cylinders"),
                )
                if row_array_size is not None and int(row_array_size) != array_size:
                    continue

            period = _float_from_row(
                row,
                ("period", "T", "period_s", "wave_period_s", "Wave period, T (s)"),
            )
            if period is None:
                print(f"Missing period field in {path}; skipping R_loc curve row.")
                continue
            if not PERIOD_RANGE[0] <= period <= PERIOD_RANGE[1]:
                continue

            if has_direct_ratio:
                rloc = _float_from_row(row, ("center_max_to_mean_ratio",))
            else:
                center_max_abs = _float_from_row(row, ("center_max_abs",))
                center_mean_abs = _float_from_row(row, ("center_mean_abs",))
                rloc = None
                if center_max_abs is not None and center_mean_abs not in (None, 0.0):
                    rloc = center_max_abs / center_mean_abs
            if rloc is None:
                print(
                    f"Missing usable R_loc value in {path}; skipping row at T={period:.3f}."
                )
                continue
            points.append((period, rloc))

    points.sort(key=lambda item: item[0])
    if not points:
        print(f"No usable R_loc points found in {path} for T=0.85-1.05 s.")
    return points


def _load_rloc_curves() -> dict[int, list[tuple[float, float]]]:
    """Load N=4, 6, and 8 R_loc refined curves from available CSV files."""
    curves: dict[int, list[tuple[float, float]]] = {}
    for array_size in (4, 6, 8):
        combined_points = _read_rloc_curve(REFINED_COMBINED_PATH, array_size)
        if combined_points:
            curves[array_size] = combined_points
            print(f"Using {REFINED_COMBINED_PATH} for N={array_size} R_loc curve.")
            continue

        summary_path = REFINED_SUMMARY_PATHS[array_size]
        summary_points = _read_rloc_curve(summary_path)
        if summary_points:
            curves[array_size] = summary_points
            print(f"Using {summary_path} for N={array_size} R_loc curve.")
        else:
            print(
                f"R_loc curve for N={array_size} was not generated because source data are missing."
            )
    return curves


def _save_rloc_figure() -> None:
    """Save the refined R_loc curve figure without fabricating missing curves."""
    curves = _load_rloc_curves()
    if not curves:
        print(
            f"No R_loc curves plotted in {RLOC_FIGURE_PATH}: "
            "no real refined R_loc curve data were available."
        )

    fig, ax = plt.subplots(figsize=(6.5, 4.2), constrained_layout=True)
    styles = {
        4: {"marker": "o", "color": "#1f77b4"},
        6: {"marker": "s", "color": "#ff7f0e"},
        8: {"marker": "^", "color": "#2ca02c"},
    }
    line_handles = []
    for array_size in (4, 6, 8):
        points = curves.get(array_size)
        if not points:
            continue
        periods = [point[0] for point in points]
        values = [point[1] for point in points]
        (line,) = ax.plot(
            periods,
            values,
            linewidth=1.8,
            markersize=4.2,
            label=f"N={array_size}",
            **styles[array_size],
        )
        line_handles.append(line)

    span = ax.axvspan(
        LOWER_BOUNDARY_INTERVAL[0],
        LOWER_BOUNDARY_INTERVAL[1],
        color="0.75",
        alpha=0.45,
        label="Lower-boundary inspection interval",
    )
    ax.set_xlim(*PERIOD_RANGE)
    ax.set_xlabel("Wave period, T (s)")
    ax.set_ylabel("Localization indicator, R_loc")
    ax.grid(True, color="0.88", linewidth=0.8)
    ax.legend(handles=[*line_handles, span], frameon=False)
    fig.savefig(RLOC_FIGURE_PATH, dpi=300)
    plt.close(fig)
    print(RLOC_FIGURE_PATH)


def _save_grouped_bar_figure(
    data: dict[int, tuple[float, float, float, float, float]],
    ylabel: str,
    output_path: Path,
) -> None:
    """Save a P0-P4 grouped bar chart for N=4, 6, and 8."""
    probes = ("P0", "P1", "P2", "P3", "P4")
    x_positions = list(range(len(probes)))
    width = 0.24
    offsets = {4: -width, 6: 0.0, 8: width}
    colors = {4: "#1f77b4", 6: "#ff7f0e", 8: "#2ca02c"}

    fig, ax = plt.subplots(figsize=(6.5, 4.0), constrained_layout=True)
    for array_size in (4, 6, 8):
        ax.bar(
            [x + offsets[array_size] for x in x_positions],
            data[array_size],
            width=width,
            label=f"N={array_size}",
            color=colors[array_size],
        )
    ax.set_xticks(x_positions, probes)
    ax.set_xlabel("Central probe")
    ax.set_ylabel(ylabel)
    ax.grid(True, axis="y", color="0.88", linewidth=0.8)
    ax.legend(frameon=False)
    fig.savefig(output_path, dpi=300)
    plt.close(fig)
    print(output_path)


def generate_figures() -> None:
    """Generate the three Section 3.2 paper figure files."""
    ensure_output_dir()
    _save_rloc_figure()
    _save_grouped_bar_figure(
        {
            4: (1.144686, 1.181162, 1.138369, 1.129854, 1.129854),
            6: (1.251260, 1.285170, 1.200618, 1.252795, 1.252795),
            8: (1.375957, 1.418578, 1.297806, 1.370118, 1.370118),
        },
        "Peak response amplitude",
        PEAK_VALUE_FIGURE_PATH,
    )
    _save_grouped_bar_figure(
        {
            4: (0.96, 0.90, 1.02, 0.97, 0.97),
            6: (0.97, 0.90, 1.04, 0.97, 0.97),
            8: (0.99, 0.94, 1.05, 0.99, 0.99),
        },
        "Peak period, T (s)",
        PEAK_PERIOD_FIGURE_PATH,
    )


def main() -> None:
    """Write Section 3.2 paper outputs."""
    ensure_output_dir()
    write_table(RECORDS)
    print(TABLE_PATH)
    write_draft()
    print(DRAFT_PATH)
    generate_figures()


if __name__ == "__main__":
    main()
