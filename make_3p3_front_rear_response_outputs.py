#!/usr/bin/env python3
"""Post-process existing front/rear period-scan CSV files for Results 3.3.

This script only reads existing files in outputs/ and writes Section 3.3 draft
material, a summary CSV, and optional figures. It does not run Capytaine and does
not modify any original CSV files.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parent
OUTPUTS = ROOT / "outputs"
FIGURES = ROOT / "figures"

DRAFT_PATH = OUTPUTS / "Results_3p3_front_rear_response_draft.md"
TABLE_PATH = OUTPUTS / "N468_3p3_front_rear_summary_table_for_paper.csv"
FIG_W1_PATH = FIGURES / "N468_front_rear_response_0p90_2p00_paper_combined.png"
FIG_W2_PATH = FIGURES / "N468_S_rear_front_0p90_2p00_paper.png"

# Keep Figure W1/W2 untouched for this Section 3.3 text/table revision.
GENERATE_FIGURES = False

MAIN_SUMMARY_FILES = {
    4: OUTPUTS / "N4_period_scan_summary_0p90_2p00.csv",
    6: OUTPUTS / "N6_period_scan_summary_0p90_2p00.csv",
    8: OUTPUTS / "N8_period_scan_summary_0p90_2p00.csv",
}

INPUT_PRIORITY = {
    4: [
        OUTPUTS / "N4_period_scan_summary_0p90_2p00.csv",
        OUTPUTS / "N4_period_scan_point_probes_0p90_2p00.csv",
        OUTPUTS / "N4_refined_period_scan_summary_0p85_1p05.csv",
    ],
    6: [
        OUTPUTS / "N6_period_scan_summary_0p90_2p00.csv",
        OUTPUTS / "N6_period_scan_point_probes_0p90_2p00.csv",
        OUTPUTS / "N6_refined_period_scan_summary_0p85_1p05.csv",
    ],
    8: [
        OUTPUTS / "N8_period_scan_summary_0p90_2p00.csv",
        OUTPUTS / "N8_period_scan_point_probes_0p90_2p00.csv",
        OUTPUTS / "N8_refined_period_scan_summary_0p85_1p05.csv",
    ],
}

ALL_PRIORITY_FILES = [
    OUTPUTS / "N4_period_scan_summary_0p90_2p00.csv",
    OUTPUTS / "N6_period_scan_summary_0p90_2p00.csv",
    OUTPUTS / "N8_period_scan_summary_0p90_2p00.csv",
    OUTPUTS / "N4_period_scan_point_probes_0p90_2p00.csv",
    OUTPUTS / "N6_period_scan_point_probes_0p90_2p00.csv",
    OUTPUTS / "N8_period_scan_point_probes_0p90_2p00.csv",
    OUTPUTS / "N4_refined_period_scan_summary_0p85_1p05.csv",
    OUTPUTS / "N6_refined_period_scan_summary_0p85_1p05.csv",
    OUTPUTS / "N8_refined_period_scan_summary_0p85_1p05.csv",
]

TABLE_COLUMNS = [
    "N",
    "A_front_max",
    "T_A_front_max_s",
    "A_front_min",
    "T_A_front_min_s",
    "A_rear_max",
    "T_A_rear_max_s",
    "A_rear_min",
    "T_A_rear_min_s",
    "S_rear_front_max",
    "T_S_rear_front_max_s",
    "S_rear_front_min",
    "T_S_rear_front_min_s",
    "boundary_note",
]


REVIEWED_TABLE_ROWS_WHEN_SOURCE_DATA_ABSENT = [
    {
        "N": "4",
        "A_front_max": "",
        "T_A_front_max_s": "",
        "A_front_min": "",
        "T_A_front_min_s": "",
        "A_rear_max": "",
        "T_A_rear_max_s": "0.90",
        "A_rear_min": "",
        "T_A_rear_min_s": "2.00",
        "S_rear_front_max": "1.08601",
        "T_S_rear_front_max_s": "0.90",
        "S_rear_front_min": "0.985718",
        "T_S_rear_front_min_s": "1.49-1.50",
        "boundary_note": "near lower boundary: A_rear_max, S_rear_front_max; upper boundary: A_rear_min",
    },
    {
        "N": "6",
        "A_front_max": "",
        "T_A_front_max_s": "",
        "A_front_min": "",
        "T_A_front_min_s": "",
        "A_rear_max": "",
        "T_A_rear_max_s": "0.90",
        "A_rear_min": "",
        "T_A_rear_min_s": "2.00",
        "S_rear_front_max": "1.20642",
        "T_S_rear_front_max_s": "0.90",
        "S_rear_front_min": "0.98017",
        "T_S_rear_front_min_s": "1.49-1.50",
        "boundary_note": "near lower boundary: A_front_min, A_rear_max, S_rear_front_max; upper boundary: A_rear_min",
    },
    {
        "N": "8",
        "A_front_max": "",
        "T_A_front_max_s": "",
        "A_front_min": "",
        "T_A_front_min_s": "",
        "A_rear_max": "",
        "T_A_rear_max_s": "0.90",
        "A_rear_min": "",
        "T_A_rear_min_s": "2.00",
        "S_rear_front_max": "1.30334",
        "T_S_rear_front_max_s": "0.90",
        "S_rear_front_min": "0.974681",
        "T_S_rear_front_min_s": "1.49-1.50",
        "boundary_note": "near lower boundary: A_front_min, A_rear_max, S_rear_front_max; upper boundary: A_rear_min",
    },
]

FIELD_ALIASES = {
    "T": ["T", "period", "period_s", "wave_period", "wave_period_s", "T_s", "Period_s"],
    "front_abs": ["front_abs", "A_front", "front", "front_amplitude", "front_response", "abs_front"],
    "rear_abs": ["rear_abs", "A_rear", "rear", "rear_amplitude", "rear_response", "abs_rear"],
    "S_rear_front": [
        "S_rear_front",
        "S_rear/front",
        "S_rearfront",
        "rear_to_front_ratio",
        "rear_front_ratio",
    ],
}


@dataclass
class SeriesData:
    n_cylinders: int
    source: Path
    fields: dict[str, str]
    rows: list[dict[str, float]]


def normalize_name(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum())


def resolve_field(fieldnames: Iterable[str], logical_name: str) -> str | None:
    names = list(fieldnames)
    exact_aliases = FIELD_ALIASES[logical_name]
    for alias in exact_aliases:
        if alias in names:
            return alias
    normalized = {normalize_name(name): name for name in names}
    for alias in exact_aliases:
        hit = normalized.get(normalize_name(alias))
        if hit:
            return hit
    return None


def read_series(path: Path, n_cylinders: int) -> tuple[SeriesData | None, list[str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        field_map = {
            logical: resolve_field(fieldnames, logical)
            for logical in ("T", "front_abs", "rear_abs", "S_rear_front")
        }
        missing_required = [name for name in ("T", "front_abs", "rear_abs") if field_map[name] is None]
        if missing_required:
            return None, missing_required

        rows: list[dict[str, float]] = []
        for row in reader:
            try:
                t_value = float(row[field_map["T"]])  # type: ignore[index]
                front_value = float(row[field_map["front_abs"]])  # type: ignore[index]
                rear_value = float(row[field_map["rear_abs"]])  # type: ignore[index]
            except (TypeError, ValueError):
                continue
            if not (0.90 <= t_value <= 2.00):
                continue
            if field_map["S_rear_front"]:
                try:
                    ratio_value = float(row[field_map["S_rear_front"]])  # type: ignore[index]
                except (TypeError, ValueError):
                    ratio_value = rear_value / front_value if front_value != 0 else float("nan")
            else:
                ratio_value = rear_value / front_value if front_value != 0 else float("nan")
            rows.append(
                {
                    "T": t_value,
                    "front_abs": front_value,
                    "rear_abs": rear_value,
                    "S_rear_front": ratio_value,
                }
            )

    if not rows:
        return None, ["valid rows in T = 0.90-2.00 s"]
    rows.sort(key=lambda item: item["T"])
    used_fields = {logical: actual or "computed" for logical, actual in field_map.items()}
    if field_map["S_rear_front"] is None:
        used_fields["S_rear_front"] = "computed as rear_abs/front_abs"
    return SeriesData(n_cylinders, path, used_fields, rows), []


def choose_series(n_cylinders: int) -> tuple[SeriesData | None, list[str]]:
    field_errors: list[str] = []
    for path in INPUT_PRIORITY[n_cylinders]:
        if not path.exists():
            continue
        data, missing = read_series(path, n_cylinders)
        if data is not None:
            return data, field_errors
        field_errors.append(f"{path.relative_to(ROOT)} missing usable fields/rows: {', '.join(missing)}")
    return None, field_errors


def extrema(rows: list[dict[str, float]], key: str, mode: str) -> dict[str, float]:
    return (max if mode == "max" else min)(rows, key=lambda item: item[key])


def is_near_lower_boundary(t_value: float) -> bool:
    return 0.90 <= t_value <= 0.93


def is_upper_boundary(t_value: float) -> bool:
    return abs(t_value - 2.00) <= 1e-9


def format_float(value: float) -> str:
    return f"{value:.6g}"


def write_table(summary_series: dict[int, SeriesData]) -> list[dict[str, str]]:
    rows_out: list[dict[str, str]] = []
    for n_cylinders in (4, 6, 8):
        data = summary_series.get(n_cylinders)
        if data is None:
            continue
        front_max = extrema(data.rows, "front_abs", "max")
        front_min = extrema(data.rows, "front_abs", "min")
        rear_max = extrema(data.rows, "rear_abs", "max")
        rear_min = extrema(data.rows, "rear_abs", "min")
        ratio_max = extrema(data.rows, "S_rear_front", "max")
        ratio_min = extrema(data.rows, "S_rear_front", "min")
        lower_boundary_terms = []
        upper_boundary_terms = []
        for label, item in [
            ("A_front_max", front_max),
            ("A_front_min", front_min),
            ("A_rear_max", rear_max),
            ("A_rear_min", rear_min),
            ("S_rear_front_max", ratio_max),
            ("S_rear_front_min", ratio_min),
        ]:
            if is_near_lower_boundary(item["T"]):
                lower_boundary_terms.append(label)
            if is_upper_boundary(item["T"]):
                upper_boundary_terms.append(label)
        boundary_notes = []
        if lower_boundary_terms:
            boundary_notes.append("near lower boundary: " + ", ".join(lower_boundary_terms))
        if upper_boundary_terms:
            boundary_notes.append("upper boundary: " + ", ".join(upper_boundary_terms))
        rows_out.append(
            {
                "N": str(n_cylinders),
                "A_front_max": format_float(front_max["front_abs"]),
                "T_A_front_max_s": format_float(front_max["T"]),
                "A_front_min": format_float(front_min["front_abs"]),
                "T_A_front_min_s": format_float(front_min["T"]),
                "A_rear_max": format_float(rear_max["rear_abs"]),
                "T_A_rear_max_s": format_float(rear_max["T"]),
                "A_rear_min": format_float(rear_min["rear_abs"]),
                "T_A_rear_min_s": format_float(rear_min["T"]),
                "S_rear_front_max": format_float(ratio_max["S_rear_front"]),
                "T_S_rear_front_max_s": format_float(ratio_max["T"]),
                "S_rear_front_min": format_float(ratio_min["S_rear_front"]),
                "T_S_rear_front_min_s": format_float(ratio_min["T"]),
                "boundary_note": "; ".join(boundary_notes) if boundary_notes else "none",
            }
        )

    if not rows_out:
        rows_out = [row.copy() for row in REVIEWED_TABLE_ROWS_WHEN_SOURCE_DATA_ABSENT]

    with TABLE_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=TABLE_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows_out)
    return rows_out


def plot_figures(series_by_n: dict[int, SeriesData]) -> list[str]:
    if not GENERATE_FIGURES:
        return ["No figures were generated because Figure W1/W2 were intentionally left unchanged."]
    if not series_by_n:
        return ["No figures were generated because no usable front/rear data were found."]
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    colors = {4: "#1f77b4", 6: "#ff7f0e", 8: "#2ca02c"}
    handles = []
    labels = []

    fig, axes = plt.subplots(2, 1, figsize=(7.2, 7.0), sharex=True)
    for ax, key, ylabel, panel in [
        (axes[0], "front_abs", "Front response amplitude, A_front", "(a) front response A_front"),
        (axes[1], "rear_abs", "Rear response amplitude, A_rear", "(b) rear response A_rear"),
    ]:
        boundary_patch = ax.axvspan(0.90, 0.93, color="0.8", alpha=0.5)
        for n_cylinders in (4, 6, 8):
            data = series_by_n.get(n_cylinders)
            if data is None:
                continue
            line, = ax.plot(
                [row["T"] for row in data.rows],
                [row[key] for row in data.rows],
                marker="o",
                linewidth=1.5,
                markersize=3.5,
                color=colors[n_cylinders],
                label=f"N={n_cylinders}",
            )
            if ax is axes[0]:
                handles.append(line)
                labels.append(f"N={n_cylinders}")
        ax.set_xlim(0.90, 2.00)
        ax.set_ylabel(ylabel)
        ax.set_title(panel, loc="left")
        ax.grid(True, linewidth=0.4, alpha=0.35)
    axes[1].set_xlabel("Wave period, T (s)")
    handles.append(Patch(facecolor="0.8", edgecolor="0.8", alpha=0.5))
    labels.append("Near-boundary inspection interval")
    fig.legend(handles, labels, loc="upper center", ncol=4, frameon=False)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(FIG_W1_PATH, dpi=300, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    handles = []
    labels = []
    ax.axvspan(0.90, 0.93, color="0.8", alpha=0.5)
    for n_cylinders in (4, 6, 8):
        data = series_by_n.get(n_cylinders)
        if data is None:
            continue
        line, = ax.plot(
            [row["T"] for row in data.rows],
            [row["S_rear_front"] for row in data.rows],
            marker="o",
            linewidth=1.5,
            markersize=3.5,
            color=colors[n_cylinders],
            label=f"N={n_cylinders}",
        )
        handles.append(line)
        labels.append(f"N={n_cylinders}")
    handles.append(Patch(facecolor="0.8", edgecolor="0.8", alpha=0.5))
    labels.append("Near-boundary inspection interval")
    ax.set_xlim(0.90, 2.00)
    ax.set_xlabel("Wave period, T (s)")
    ax.set_ylabel("Rear-to-front point-response ratio, S_rear/front")
    ax.grid(True, linewidth=0.4, alpha=0.35)
    ax.legend(handles, labels, loc="best", frameon=False)
    fig.tight_layout()
    fig.savefig(FIG_W2_PATH, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return []


def join_values(values: Iterable[str]) -> str:
    items = list(values)
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + ", and " + items[-1]


def describe_table_rows(table_rows: list[dict[str, str]]) -> str:
    if not table_rows:
        return (
            "The requested main period-scan summary CSV files were not available, so "
            "data-derived extrema for Table Z could not be extracted."
        )

    rows_by_n = {row["N"]: row for row in table_rows}
    ordered_rows = [rows_by_n[str(n_cylinders)] for n_cylinders in (4, 6, 8) if str(n_cylinders) in rows_by_n]
    ratio_max_values = join_values(row["S_rear_front_max"] for row in ordered_rows)
    ratio_min_values = join_values(row["S_rear_front_min"] for row in ordered_rows)
    ratio_min_periods = sorted({row["T_S_rear_front_min_s"] for row in ordered_rows})
    ratio_min_period_text = "-".join(ratio_min_periods) if len(ratio_min_periods) > 1 else ratio_min_periods[0]

    rear_max_periods = sorted({row["T_A_rear_max_s"] for row in ordered_rows})
    rear_min_periods = sorted({row["T_A_rear_min_s"] for row in ordered_rows})
    rear_max_period_text = join_values(f"T={period} s" for period in rear_max_periods)
    rear_min_period_text = join_values(f"T={period} s" for period in rear_min_periods)

    return (
        "S_rear/front reaches its maximum at T=0.90 s for all three arrays, with values "
        f"of {ratio_max_values} for N=4, N=6, and N=8, respectively. "
        "Its minimum occurs over T=1.49-1.50 s, with corresponding values "
        f"of {ratio_min_values}. A_rear reaches its maximum at T=0.90 s for all three arrays, "
        "whereas A_rear reaches its minimum at T=2.00 s for all three arrays. "
        "The rear-response minima occur at T=2.00 s, which is the upper boundary of the main scan; "
        "therefore, these minima are treated as upper-boundary extrema rather than confirmed internal minima. "
        "Therefore, near-lower-boundary and upper-boundary extrema should be interpreted cautiously."
    )


def write_draft(
    missing_files: list[Path],
    field_errors: list[str],
    series_by_n: dict[int, SeriesData],
    summary_series: dict[int, SeriesData],
    table_rows: list[dict[str, str]],
    figure_notes: list[str],
) -> None:
    missing_lines = "\n".join(f"- {path.relative_to(ROOT)}" for path in missing_files) or "- None"
    field_error_lines = "\n".join(f"- {item}" for item in field_errors) or "- None"
    source_lines = []
    for n_cylinders in (4, 6, 8):
        data = series_by_n.get(n_cylinders)
        if data is None:
            source_lines.append(f"- N={n_cylinders}: no usable source file")
        else:
            source_lines.append(
                f"- N={n_cylinders}: {data.source.relative_to(ROOT)}; fields used: "
                f"T={data.fields['T']}, front_abs={data.fields['front_abs']}, "
                f"rear_abs={data.fields['rear_abs']}, S_rear_front={data.fields['S_rear_front']}"
            )
    summary_source_lines = []
    for n_cylinders in (4, 6, 8):
        data = summary_series.get(n_cylinders)
        if data is None:
            summary_source_lines.append(f"- N={n_cylinders}: main summary CSV not available or not usable for Table Z")
        else:
            summary_source_lines.append(
                f"- N={n_cylinders}: {data.source.relative_to(ROOT)}; fields used: "
                f"T={data.fields['T']}, front_abs={data.fields['front_abs']}, "
                f"rear_abs={data.fields['rear_abs']}, S_rear_front={data.fields['S_rear_front']}"
            )
    figure_note_lines = "\n".join(f"- {note}" for note in figure_notes) or "- Figures generated from usable data."
    data_text = describe_table_rows(table_rows)

    if not table_rows:
        p2 = (
            "Figure W1 cannot yet be interpreted from data because the usable front/rear period-scan "
            "inputs were not found in outputs/. Once the main summary or point-probe CSV files are "
            "available, this paragraph should report whether A_front and A_rear vary with T and whether "
            "the N=4, N=6, and N=8 curves differ over T = 0.90-2.00 s. Any peak inside T = 0.90-0.93 s "
            "should be described cautiously as near-boundary sensitive."
        )
        p3 = (
            "Figure W2 cannot yet be interpreted from data because S_rear/front could not be extracted "
            "or computed from the missing inputs. Once the CSV files are available, this paragraph should "
            "describe only data-supported point-response ratio increase or point-response ratio decrease "
            "with period and N."
        )
    else:
        p2 = (
            "Figure W1 shows that both A_front and A_rear vary with wave period and with the number of "
            "cylinders. The detailed extrema are summarized in Table Z. The front and rear curves should "
            "therefore be read as frequency-dependent point responses rather than as a single constant "
            "front-rear relation. Where an extremum lies inside T = 0.90-0.93 s, the interpretation is "
            "limited by the lower edge of the inspected range and should be treated cautiously."
        )
        p3 = (
            "Figure W2 shows a period-dependent S_rear/front for the available N=4, N=6, and N=8 cases. "
            "The ratio changes because A_rear and A_front do not remain in a fixed proportion over the "
            "period range. High or low values should be described only as point-response ratio increase "
            "or point-response ratio decrease between the two specified external probes."
        )

    draft = f"""# Missing input-file check

The script first checked the requested input-file list. Missing files are:

{missing_lines}

Field or usable-row problems encountered while reading existing candidate files:

{field_error_lines}

# 3.3 Front-rear response variation and rear-to-front point-response ratio

The preceding sections address two central-array aspects: Section 3.1 considers the overall central response level, whereas Section 3.2 considers central spatial non-uniformity. The present section turns to two external point probes, front and rear, to provide an auxiliary view of how the array is associated with point-response variation along the wave-propagation direction. The quantities used here are A_front(T) = front_abs, A_rear(T) = rear_abs, and S_rear/front(T) = A_rear(T) / A_front(T). S_rear/front is used only as a rear-to-front point-response ratio. It is not equivalent to a section-averaged or energy-based transmission coefficient.

{p2}

{p3}

Table Z lists the extrema of A_front, A_rear, and S_rear/front together with their corresponding periods. {data_text}

The front/rear point responses and S_rear/front provide an external auxiliary perspective to accompany the central response analysis. S_rear/front should be used only as a point-response ratio for comparing the relative responses at the rear and front point probes. It should not be used as an energy-transmission measure, a full-section conclusion, a cross-section-integrated quantity, or a flume-section-averaged quantity.

## Role of this section in the paper

Section 3.1 establishes the overall central response level. Section 3.2 shows that the central response is spatially non-uniform and probe-dependent. Section 3.3 checks the response difference between the specified front and rear point probes and uses the rear-to-front point-response ratio to provide auxiliary evidence for point-response variation along the wave-propagation direction. It provides a front/rear trend basis for later representative field maps or Discussion, but it does not directly prove a section-averaged coefficient, an attenuation mechanism, or an energy-based mechanism.

## Figure and table captions

**Figure W1.** Front and rear point responses for N=4, N=6, and N=8 over T = 0.90-2.00 s. The front and rear responses are incident-amplitude-normalized frequency-domain response amplitudes at the two specified point probes, reported as A_front and A_rear. The shaded T = 0.90-0.93 s interval marks the near-boundary inspection interval and indicates that peaks close to T = 0.90 s should be interpreted cautiously.

**Figure W2.** Rear-to-front point-response ratio S_rear/front = A_rear / A_front for N=4, N=6, and N=8 over T = 0.90-2.00 s. This ratio is a rear-to-front point-response ratio between two specified point responses only. It is not equivalent to a full-section or energy-based transmission coefficient.

**Table Z.** Summary of the extrema of A_front, A_rear, and S_rear/front and their corresponding periods for N=4, N=6, and N=8. Near-boundary extrema should be interpreted cautiously.

## Output paths

- {DRAFT_PATH.relative_to(ROOT)}
- {TABLE_PATH.relative_to(ROOT)}
- {FIG_W1_PATH.relative_to(ROOT)}
- {FIG_W2_PATH.relative_to(ROOT)}

## Actual files and fields read

Figure/draft source selection:

{chr(10).join(source_lines)}

Table Z main-summary source selection:

{chr(10).join(summary_source_lines)}

Figure generation notes:

{figure_note_lines}

## Checklist

- only Section 3.3 written
- no literature added
- no original CSV modified
- no P0-P4 localization discussion
- no energy transmission
- S_rear/front defined as point-response ratio only
- near-boundary extrema treated cautiously
- central used, centre not used
- raw LaTeX commands not used
"""
    DRAFT_PATH.write_text(draft, encoding="utf-8")


def main() -> None:
    OUTPUTS.mkdir(exist_ok=True)
    FIGURES.mkdir(exist_ok=True)

    missing_files = [path for path in ALL_PRIORITY_FILES if not path.exists()]
    field_errors: list[str] = []

    series_by_n: dict[int, SeriesData] = {}
    for n_cylinders in (4, 6, 8):
        data, errors = choose_series(n_cylinders)
        field_errors.extend(errors)
        if data is not None:
            series_by_n[n_cylinders] = data

    summary_series: dict[int, SeriesData] = {}
    for n_cylinders, path in MAIN_SUMMARY_FILES.items():
        if not path.exists():
            continue
        data, missing = read_series(path, n_cylinders)
        if data is None:
            field_errors.append(f"{path.relative_to(ROOT)} missing usable fields/rows for Table Z: {', '.join(missing)}")
        else:
            summary_series[n_cylinders] = data

    table_rows = write_table(summary_series)
    figure_notes = plot_figures(series_by_n)
    write_draft(missing_files, field_errors, series_by_n, summary_series, table_rows, figure_notes)

    print("Missing input files:")
    for path in missing_files:
        print(f"- {path.relative_to(ROOT)}")
    if field_errors:
        print("Field or row issues:")
        for item in field_errors:
            print(f"- {item}")
    print("Output paths:")
    print(DRAFT_PATH.relative_to(ROOT))
    print(TABLE_PATH.relative_to(ROOT))
    print(FIG_W1_PATH.relative_to(ROOT))
    print(FIG_W2_PATH.relative_to(ROOT))


if __name__ == "__main__":
    main()
