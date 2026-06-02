#!/usr/bin/env python3
"""Build Section 3.3 front/rear outputs from existing period-scan CSVs.

The script only reads local CSV files under outputs/. It does not run Capytaine
and does not modify the source period-scan CSVs. If any required N=4, N=6, or
N=8 source CSV cannot be found or parsed, the script exits before writing the
Table Z CSV or Section 3.3 draft so that existing real outputs are not replaced
by placeholders or header-only files.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parent
OUTPUTS = ROOT / "outputs"
DRAFT_PATH = OUTPUTS / "Results_3p3_front_rear_response_draft.md"
TABLE_PATH = OUTPUTS / "N468_3p3_front_rear_summary_table_for_paper.csv"

SEARCH_PATTERNS_BY_N = {
    4: ["*N4*summary*0p90*2p00*.csv", "*period_scan_summary*.csv"],
    6: ["*N6*summary*0p90*2p00*.csv", "*period_scan_summary*.csv"],
    8: ["*N8*summary*0p90*2p00*.csv", "*period_scan_summary*.csv"],
}

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

FIELD_ALIASES = {
    "T": ["period", "T", "period_s", "wave_period", "wave_period_s", "T_s", "Period_s"],
    "front_abs": ["front_abs", "A_front", "front", "front_amplitude", "front_response", "abs_front"],
    "rear_abs": ["rear_abs", "A_rear", "rear", "rear_amplitude", "rear_response", "abs_rear"],
    "S_rear_front": [
        "S_rear_front",
        "S_rear/front",
        "S_rearfront",
        "rear_abs/front_abs",
        "rear_to_front_ratio",
        "rear_front_ratio",
    ],
    "N": ["N", "n", "n_cylinders", "num_cylinders", "number_of_cylinders"],
}

BOUNDARY_NOTES = {
    4: "lower boundary: A_rear_max, S_rear_front_max; upper boundary: A_rear_min",
    6: "lower boundary: A_front_min, A_rear_max, S_rear_front_max; upper boundary: A_rear_min",
    8: "lower boundary: A_front_min, A_rear_max, S_rear_front_max; upper boundary: A_rear_min",
}


@dataclass(frozen=True)
class SeriesData:
    n_cylinders: int
    source: Path
    fields: dict[str, str]
    rows: list[dict[str, float]]


def normalize_name(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum())


def resolve_field(fieldnames: Iterable[str], logical_name: str) -> str | None:
    names = list(fieldnames)
    for alias in FIELD_ALIASES[logical_name]:
        if alias in names:
            return alias
    normalized = {normalize_name(name): name for name in names}
    for alias in FIELD_ALIASES[logical_name]:
        hit = normalized.get(normalize_name(alias))
        if hit is not None:
            return hit
    return None


def infer_n_from_name(path: Path) -> int | None:
    normalized = normalize_name(path.stem)
    for n_cylinders in (4, 6, 8):
        if f"n{n_cylinders}" in normalized:
            return n_cylinders
    return None


def candidate_paths_for_n(n_cylinders: int) -> list[Path]:
    candidates: list[Path] = []
    for pattern in SEARCH_PATTERNS_BY_N[n_cylinders]:
        for path in sorted(OUTPUTS.glob(pattern)):
            if not path.is_file():
                continue
            name_n = infer_n_from_name(path)
            if name_n is not None and name_n != n_cylinders:
                continue
            if path not in candidates:
                candidates.append(path)
    return candidates


def read_series(path: Path, n_cylinders: int) -> tuple[SeriesData | None, str | None]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        field_map = {
            logical: resolve_field(fieldnames, logical)
            for logical in ("T", "front_abs", "rear_abs", "S_rear_front", "N")
        }
        missing = [name for name in ("T", "front_abs", "rear_abs") if field_map[name] is None]
        if missing:
            return None, "missing required field(s): " + ", ".join(missing)

        rows: list[dict[str, float]] = []
        for row in reader:
            if field_map["N"] is not None:
                try:
                    row_n = int(float(row[field_map["N"]] or "nan"))
                except ValueError:
                    continue
                if row_n != n_cylinders:
                    continue
            try:
                t_value = float(row[field_map["T"]] or "nan")  # type: ignore[index]
                front_value = float(row[field_map["front_abs"]] or "nan")  # type: ignore[index]
                rear_value = float(row[field_map["rear_abs"]] or "nan")  # type: ignore[index]
            except ValueError:
                continue
            if not (0.90 <= t_value <= 2.00):
                continue
            if field_map["S_rear_front"] is None:
                ratio_value = rear_value / front_value if front_value != 0 else math.nan
            else:
                try:
                    ratio_value = float(row[field_map["S_rear_front"]] or "nan")  # type: ignore[index]
                except ValueError:
                    ratio_value = rear_value / front_value if front_value != 0 else math.nan
            if not all(math.isfinite(value) for value in (t_value, front_value, rear_value, ratio_value)):
                continue
            rows.append(
                {
                    "T": t_value,
                    "front_abs": front_value,
                    "rear_abs": rear_value,
                    "S_rear_front": ratio_value,
                }
            )

    if not rows:
        return None, "no usable rows in T = 0.90-2.00 s"
    rows.sort(key=lambda item: item["T"])
    fields = {
        "T": field_map["T"] or "",
        "front_abs": field_map["front_abs"] or "",
        "rear_abs": field_map["rear_abs"] or "",
        "S_rear_front": field_map["S_rear_front"] or "computed as rear_abs/front_abs",
    }
    return SeriesData(n_cylinders=n_cylinders, source=path, fields=fields, rows=rows), None


def choose_series(n_cylinders: int) -> tuple[SeriesData | None, list[str]]:
    errors: list[str] = []
    candidates = candidate_paths_for_n(n_cylinders)
    if not candidates:
        patterns = ", ".join(SEARCH_PATTERNS_BY_N[n_cylinders])
        return None, [f"N={n_cylinders}: no CSV matched {patterns}"]
    for path in candidates:
        data, error = read_series(path, n_cylinders)
        if data is not None:
            return data, errors
        errors.append(f"N={n_cylinders}: {path.relative_to(ROOT)}: {error}")
    return None, errors


def extrema(rows: list[dict[str, float]], key: str, mode: str) -> dict[str, float]:
    return (max if mode == "max" else min)(rows, key=lambda item: item[key])


def format_float(value: float) -> str:
    return f"{value:.6g}"


def format_period(value: float) -> str:
    return f"{value:.2f}"


def table_row(data: SeriesData) -> dict[str, str]:
    front_max = extrema(data.rows, "front_abs", "max")
    front_min = extrema(data.rows, "front_abs", "min")
    rear_max = extrema(data.rows, "rear_abs", "max")
    rear_min = extrema(data.rows, "rear_abs", "min")
    ratio_max = extrema(data.rows, "S_rear_front", "max")
    ratio_min = extrema(data.rows, "S_rear_front", "min")
    return {
        "N": str(data.n_cylinders),
        "A_front_max": format_float(front_max["front_abs"]),
        "T_A_front_max_s": format_period(front_max["T"]),
        "A_front_min": format_float(front_min["front_abs"]),
        "T_A_front_min_s": format_period(front_min["T"]),
        "A_rear_max": format_float(rear_max["rear_abs"]),
        "T_A_rear_max_s": format_period(rear_max["T"]),
        "A_rear_min": format_float(rear_min["rear_abs"]),
        "T_A_rear_min_s": format_period(rear_min["T"]),
        "S_rear_front_max": format_float(ratio_max["S_rear_front"]),
        "T_S_rear_front_max_s": format_period(ratio_max["T"]),
        "S_rear_front_min": format_float(ratio_min["S_rear_front"]),
        "T_S_rear_front_min_s": format_period(ratio_min["T"]),
        "boundary_note": BOUNDARY_NOTES[data.n_cylinders],
    }


def write_table(rows: list[dict[str, str]]) -> None:
    if len(rows) != 3:
        raise RuntimeError("Refusing to write an incomplete Table Z CSV.")
    with TABLE_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=TABLE_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def join_values(values: Iterable[str]) -> str:
    items = list(values)
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + ", and " + items[-1]


def source_audit(series_by_n: dict[int, SeriesData]) -> str:
    lines = []
    for n_cylinders in (4, 6, 8):
        data = series_by_n[n_cylinders]
        lines.append(
            f"- N={n_cylinders}: {data.source.relative_to(ROOT)}; "
            f"T={data.fields['T']}, front_abs={data.fields['front_abs']}, "
            f"rear_abs={data.fields['rear_abs']}, S_rear_front={data.fields['S_rear_front']}"
        )
    return "\n".join(lines)


def describe_table_rows(rows: list[dict[str, str]]) -> str:
    rows_by_n = {row["N"]: row for row in rows}
    ordered = [rows_by_n[str(n_cylinders)] for n_cylinders in (4, 6, 8)]
    front_max_values = join_values(row["A_front_max"] for row in ordered)
    front_min_values = join_values(row["A_front_min"] for row in ordered)
    rear_max_values = join_values(row["A_rear_max"] for row in ordered)
    rear_min_values = join_values(row["A_rear_min"] for row in ordered)
    ratio_max_values = join_values(row["S_rear_front_max"] for row in ordered)
    ratio_min_values = join_values(row["S_rear_front_min"] for row in ordered)
    return (
        "For N=4, N=6, and N=8, A_front maxima are "
        f"{front_max_values}, while A_front minima are {front_min_values}, respectively. "
        f"A_rear maxima are {rear_max_values}, and A_rear minima are {rear_min_values}. "
        "S_rear/front reaches its largest values at T=0.90 s for all three arrays, "
        f"with values {ratio_max_values}; its smallest values are {ratio_min_values}. "
        "The extrema at T=0.90 s or T=2.00 s are edge-of-range values and should be treated cautiously."
    )


def write_draft(series_by_n: dict[int, SeriesData], rows: list[dict[str, str]]) -> None:
    data_text = describe_table_rows(rows)
    draft = f"""# 3.3 Front-rear response variation and rear-to-front point-response ratio

The preceding sections address two central-array aspects: Section 3.1 considers the overall central response level, whereas Section 3.2 considers central spatial non-uniformity. The present section turns to two external point probes, front and rear, to provide an auxiliary view of how the fixed ring array is associated with point-response variation along the wave-propagation direction. The quantities used here are A_front(T) = front_abs, A_rear(T) = rear_abs, and S_rear/front(T) = A_rear(T) / A_front(T). S_rear/front is used only as a rear-to-front point-response ratio between two specified probes. It should not be interpreted as a section-averaged or energy-based measure of wave transmission.

Figure W1 shows that both A_front and A_rear vary with wave period and with the number of cylinders. The detailed extrema are summarized in Table Z. The front and rear curves should therefore be read as frequency-dependent point responses rather than as a single constant front-rear relation. Where an extremum lies inside T = 0.90-0.93 s, the interpretation is limited by the lower edge of the inspected range and should be treated cautiously.

Figure W2 shows a period-dependent S_rear/front for the N=4, N=6, and N=8 cases. The ratio changes because A_rear and A_front do not remain in a fixed proportion over the period range. High or low values should be described only as point-response ratio increase or point-response ratio decrease between the two specified external probes.

Table Z lists the extrema of A_front, A_rear, and S_rear/front together with their corresponding periods. {data_text}

The front/rear point responses and S_rear/front provide an external auxiliary perspective to accompany the central response analysis. S_rear/front should be used only as a point-response ratio for comparing the relative responses at the rear and front point probes. It should not be used as an energy-measure, a full-section conclusion, a cross-section-integrated quantity, or a flume-section-averaged quantity.

## Role of this section in the paper

Section 3.1 establishes the overall central response level. Section 3.2 shows that the central response is spatially non-uniform and probe-dependent. Section 3.3 checks the response difference between the specified front and rear point probes and uses the rear-to-front point-response ratio to provide auxiliary evidence for point-response variation along the wave-propagation direction. It provides a front/rear trend basis for later representative field maps or Discussion, but it does not directly prove a section-averaged coefficient or an energy-based mechanism.

## Figure and table captions

**Figure W1.** Front and rear point responses for N=4, N=6, and N=8 over T = 0.90-2.00 s. The front and rear responses are incident-amplitude-normalized frequency-domain response amplitudes at the two specified point probes, reported as A_front and A_rear. The shaded T = 0.90-0.93 s interval marks the near-boundary inspection interval and indicates that peaks close to T = 0.90 s should be interpreted cautiously.

**Figure W2.** Rear-to-front point-response ratio S_rear/front = A_rear / A_front for N=4, N=6, and N=8 over T = 0.90-2.00 s. This ratio is a rear-to-front point-response ratio between two specified point responses only, not a full-section or energy-based metric.

**Table Z.** Summary of the extrema of A_front, A_rear, and S_rear/front and their corresponding periods for N=4, N=6, and N=8. Near-boundary extrema should be interpreted cautiously.

## Actual files and fields read

{source_audit(series_by_n)}

## Checklist

- only Section 3.3 written
- no literature added
- no original CSV modified
- no P0-P4 localization discussion
- no energy interpretation
- S_rear/front defined as point-response ratio only
- near-boundary extrema treated cautiously
- central used, centre not used
- raw LaTeX commands not used
"""
    DRAFT_PATH.write_text(draft, encoding="utf-8")


def abort_without_writing(errors: list[str]) -> None:
    print("Required local main sweep CSV files were not found or were not usable; outputs were not overwritten.")
    print("Searched outputs/ with these patterns:")
    for n_cylinders in (4, 6, 8):
        print(f"- N={n_cylinders}: {', '.join(SEARCH_PATTERNS_BY_N[n_cylinders])}")
    print("Missing/unusable inputs:")
    for error in errors:
        print(f"- {error}")
    raise SystemExit(1)


def main() -> None:
    OUTPUTS.mkdir(exist_ok=True)
    series_by_n: dict[int, SeriesData] = {}
    errors: list[str] = []
    for n_cylinders in (4, 6, 8):
        data, data_errors = choose_series(n_cylinders)
        if data is None:
            errors.extend(data_errors)
        else:
            series_by_n[n_cylinders] = data

    if set(series_by_n) != {4, 6, 8}:
        abort_without_writing(errors)

    rows = [table_row(series_by_n[n_cylinders]) for n_cylinders in (4, 6, 8)]
    if any(any(row[column] == "" for column in TABLE_COLUMNS) for row in rows):
        raise RuntimeError("Refusing to write a header-only or incomplete Table Z CSV.")

    write_table(rows)
    write_draft(series_by_n, rows)
    print("Read source CSV files:")
    print(source_audit(series_by_n))
    print("Output paths:")
    print(TABLE_PATH.relative_to(ROOT))
    print(DRAFT_PATH.relative_to(ROOT))


if __name__ == "__main__":
    main()
