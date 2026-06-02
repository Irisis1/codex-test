# Missing input-file check

The script first checked the requested input-file list. Missing files are:

- outputs/N4_period_scan_summary_0p90_2p00.csv
- outputs/N6_period_scan_summary_0p90_2p00.csv
- outputs/N8_period_scan_summary_0p90_2p00.csv
- outputs/N4_period_scan_point_probes_0p90_2p00.csv
- outputs/N6_period_scan_point_probes_0p90_2p00.csv
- outputs/N8_period_scan_point_probes_0p90_2p00.csv
- outputs/N4_refined_period_scan_summary_0p85_1p05.csv
- outputs/N6_refined_period_scan_summary_0p85_1p05.csv
- outputs/N8_refined_period_scan_summary_0p85_1p05.csv

Field or usable-row problems encountered while reading existing candidate files:

- None

# 3.3 Front-rear response variation and rear-to-front point-response ratio

The preceding sections address two central-array aspects: Section 3.1 considers the overall central response level, whereas Section 3.2 considers central spatial non-uniformity. The present section turns to two external point probes, front and rear, to provide an auxiliary view of how the array is associated with point-response variation along the wave-propagation direction. The quantities used here are A_front(T) = front_abs, A_rear(T) = rear_abs, and S_rear/front(T) = A_rear(T) / A_front(T). S_rear/front is used only as a rear-to-front point-response ratio. It is not equivalent to a section-averaged or energy-based transmission coefficient.

Figure W1 shows that both A_front and A_rear vary with wave period and with the number of cylinders. The detailed extrema are summarized in Table Z. The front and rear curves should therefore be read as frequency-dependent point responses rather than as a single constant front-rear relation. Where an extremum lies inside T = 0.90-0.93 s, the interpretation is limited by the lower edge of the inspected range and should be treated cautiously.

Figure W2 shows a period-dependent S_rear/front for the available N=4, N=6, and N=8 cases. The ratio changes because A_rear and A_front do not remain in a fixed proportion over the period range. High or low values should be described only as point-response ratio increase or point-response ratio decrease between the two specified external probes.

Table Z lists the extrema of A_front, A_rear, and S_rear/front together with their corresponding periods. S_rear/front reaches its maximum at T=0.90 s for all three arrays, with values of 1.08601, 1.20642, and 1.30334 for N=4, N=6, and N=8, respectively. Its minimum occurs over T=1.49-1.50 s, with corresponding values of 0.985718, 0.98017, and 0.974681. A_rear reaches its maximum at T=0.90 s for all three arrays, whereas A_rear reaches its minimum at T=2.00 s for all three arrays. The rear-response minima occur at T=2.00 s, which is the upper boundary of the main scan; therefore, these minima are treated as upper-boundary extrema rather than confirmed internal minima. Therefore, near-lower-boundary and upper-boundary extrema should be interpreted cautiously.

The front/rear point responses and S_rear/front provide an external auxiliary perspective to accompany the central response analysis. S_rear/front should be used only as a point-response ratio for comparing the relative responses at the rear and front point probes. It should not be used as an energy-transmission measure, a full-section conclusion, a cross-section-integrated quantity, or a flume-section-averaged quantity.

## Role of this section in the paper

Section 3.1 establishes the overall central response level. Section 3.2 shows that the central response is spatially non-uniform and probe-dependent. Section 3.3 checks the response difference between the specified front and rear point probes and uses the rear-to-front point-response ratio to provide auxiliary evidence for point-response variation along the wave-propagation direction. It provides a front/rear trend basis for later representative field maps or Discussion, but it does not directly prove a section-averaged coefficient, an attenuation mechanism, or an energy-based mechanism.

## Figure and table captions

**Figure W1.** Front and rear point responses for N=4, N=6, and N=8 over T = 0.90-2.00 s. The front and rear responses are incident-amplitude-normalized frequency-domain response amplitudes at the two specified point probes, reported as A_front and A_rear. The shaded T = 0.90-0.93 s interval marks the near-boundary inspection interval and indicates that peaks close to T = 0.90 s should be interpreted cautiously.

**Figure W2.** Rear-to-front point-response ratio S_rear/front = A_rear / A_front for N=4, N=6, and N=8 over T = 0.90-2.00 s. This ratio is a rear-to-front point-response ratio between two specified point responses only. It is not equivalent to a full-section or energy-based transmission coefficient.

**Table Z.** Summary of the extrema of A_front, A_rear, and S_rear/front and their corresponding periods for N=4, N=6, and N=8. Near-boundary extrema should be interpreted cautiously.

## Output paths

- outputs/Results_3p3_front_rear_response_draft.md
- outputs/N468_3p3_front_rear_summary_table_for_paper.csv
- figures/N468_front_rear_response_0p90_2p00_paper_combined.png
- figures/N468_S_rear_front_0p90_2p00_paper.png

## Actual files and fields read

Figure/draft source selection:

- N=4: no usable source file
- N=6: no usable source file
- N=8: no usable source file

Table Z main-summary source selection:

- N=4: main summary CSV not available or not usable for Table Z
- N=6: main summary CSV not available or not usable for Table Z
- N=8: main summary CSV not available or not usable for Table Z

Figure generation notes:

- No figures were generated because Figure W1/W2 were intentionally left unchanged.

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
