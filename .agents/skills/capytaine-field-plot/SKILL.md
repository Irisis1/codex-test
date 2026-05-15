---
name: capytaine-field-plot
description: Use this skill for Capytaine 2D free-surface field plotting, contour maps, selected-period visualization, shared colorbars, centre-region maps, and figure-quality control for ring-cylinder water-wave models.
---

You are working on 2D free-surface visualization for Capytaine ring-cylinder water-wave models.

Primary purpose:
Generate scientifically consistent free-surface contour plots without slowing down the full period sweep or creating misleading comparisons.

Separation rule:
- Never calculate dense 2D free-surface fields inside the complete period-sweep loop.
- First run scalar probe sweeps.
- Then select representative periods.
- Only selected periods should be used for 2D field plots.

Default selected periods:
- T = 0.98 s
- T = 1.00 s
- T = 1.02 s
- T = 1.40 s

These can be changed only when the user specifies different periods or when scalar sweep results show more appropriate peak or trough periods.

Default plotting domains:
- Global field: choose a domain large enough to include incident side, ring structure, and rear-field response.
- Centre-region field: use a smaller domain around the ring and centre region.
- Keep the same plotting domain across N = 4, 6, and 8 when comparing models.

Resolution rules:
- Exploratory grid: approximately 100–150 points in x and 80–120 points in y.
- Final publication-style grid: increase only for selected periods.
- Do not use unnecessarily dense grids during debugging.

Colorbar rules:
1. Use the same colorbar range when directly comparing N = 4, 6, and 8.
2. Use a symmetric colorbar around zero for signed free-surface elevation.
3. Use modulus or normalized amplitude only if the figure title and colorbar clearly say so.
4. Do not compare signed eta and abs(eta) in the same figure without explicit labeling.

Figure layout rules:
- For four selected periods, use a 2 × 2 layout.
- For N = 4, 6, and 8 comparison at one period, use a 1 × 3 layout.
- For multiple models and periods, avoid overcrowded figures; split into separate figures if necessary.
- Mark cylinder positions when helpful.
- Mark centre five-point probes only if the figure is about probe layout or local response interpretation.

Required labels:
- x coordinate in metres
- y coordinate in metres
- period T in seconds
- model name, for example N = 4, N = 6, or N = 8
- colorbar quantity and normalization

Scientific interpretation rules:
- Do not infer energy conservation from contour appearance alone.
- Do not describe a high-amplitude rear field as “transmission coefficient” unless it is calculated by a defined coefficient.
- Distinguish centre local enhancement from downstream wave strengthening.
- Distinguish instantaneous/signed real-part fields from complex-amplitude modulus fields.

Performance checks:
If plotting is slow, inspect:
1. grid size
2. number of selected periods
3. number of models
4. whether solver results are recomputed unnecessarily
5. whether fields are recalculated multiple times for the same period

Output rules:
- Save figures with clear names containing model number and period.
- Prefer both PNG for quick inspection and PDF/SVG for paper editing when requested.
- For Origin workflows, export the field grid as CSV only for selected periods.
- Do not overwrite final figures unless explicitly requested or using versioned filenames.

Recommended figure naming:
- field_N4_T1p00.png
- field_N6_T1p00.png
- field_N8_T1p00.png
- field_compare_N4_N6_N8_T1p00.png
- field_selected_periods_N8.png
