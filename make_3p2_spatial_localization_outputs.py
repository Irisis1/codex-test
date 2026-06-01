"""Create Section 3.2 spatial-localization text and table outputs.

This is a lightweight post-processing script only. It does not import or run
Capytaine, does not modify any source CSV files, and does not generate figures.
The numerical values are the already identified refined-scan central-response
peak values used for the Section 3.2 localization discussion.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

OUTPUT_DIR = Path("outputs")
DRAFT_PATH = OUTPUT_DIR / "Results_3p2_spatial_localization_draft.md"
TABLE_PATH = OUTPUT_DIR / "N468_3p2_spatial_localization_table_for_paper.csv"


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
    """Create the outputs directory if needed."""
    OUTPUT_DIR.mkdir(exist_ok=True)


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


def write_draft(records: tuple[SpatialLocalizationRecord, ...]) -> None:
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


def main() -> None:
    """Write Section 3.2 paper outputs."""
    ensure_output_dir()
    write_table(RECORDS)
    write_draft(RECORDS)


if __name__ == "__main__":
    main()
