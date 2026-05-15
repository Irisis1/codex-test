---
name: capytaine-sweep-postprocess
description: Use this skill for Capytaine period-sweep post-processing of fixed ring-cylinder water-wave models, including center five-point probes, front/rear probes, Mc, Kr, Kt, S_rear_front, CSV export, and avoiding dense 2D free-surface computation during sweeps.
---

You are working on a Capytaine linear potential-flow BEM project for fixed ring-cylinder arrays in water waves.

Primary purpose:
Standardize fast period-sweep post-processing and prevent inconsistent normalization, probe definitions, and unnecessary 2D field calculations.

Core physical assumptions:
- Linear potential-flow theory.
- Frequency-domain BEM.
- Fixed bodies.
- Diffraction-only problem unless the user explicitly specifies otherwise.
- No body motion should be introduced unless explicitly requested.
- Units must be metres, seconds, radians per second, and wave-amplitude units consistent with the Capytaine output.

Standard geometry parameters unless explicitly changed:
- Cylinder radius: a = 0.06 m.
- Cylinder draft / underwater length: d = 0.598 m.
- Water depth: h = 0.60 m.
- Ring radius: R = 0.30 m.
- Cylinder centre depth: z_c approximately -0.30 m.
- Models usually use N = 4, 6, or 8 cylinders placed on a single circular ring.

Standard probe definitions:
- P0 = (0.0, 0.0)
- P1 = (0.1, 0.0)
- P2 = (-0.1, 0.0)
- P3 = (0.0, 0.1)
- P4 = (0.0, -0.1)
- front = (-2.0, 0.0)
- rear = (2.0, 0.0)

Period-sweep rules:
1. Separate period sweep from 2D free-surface contour plotting.
2. During full period sweeps, compute only scalar probe responses and derived indicators.
3. Do not compute dense 2D free-surface grids inside the full period loop.
4. Use coarse or medium scans first:
   - broad exploratory scan: ΔT = 0.05 s or 0.02 s
   - local fine scan only near key bands, for example 0.90–1.06 s and 1.30–1.46 s
5. Do not silently change the scanned period range or step size.

Required output columns for each period:
- T
- omega
- center_abs_P0
- center_abs_P1
- center_abs_P2
- center_abs_P3
- center_abs_P4
- center_mean_abs
- center_max_abs
- front_abs
- rear_abs
- S_rear_front

Indicator rules:
- S_rear_front = rear_abs / front_abs, unless the user defines another formula.
- Mc must explicitly state its reference amplitude A_ref.
- Kr and Kt must explicitly state their formulas and whether they are amplitude coefficients or energy-like squared quantities.
- Do not assume Kr^2 + Kt^2 = 1 for a finite near-field probe extraction unless the extraction method is energy-flux-consistent.
- Do not present near-field probe ratios as strict far-field energy coefficients without qualification.

Normalization discipline:
1. Always identify A_ref.
2. Do not mix incident amplitude, upstream probe amplitude, and centre response as interchangeable references.
3. If the code uses incident wave amplitude, label it as A_inc.
4. If the code uses front probe amplitude, label it as front_abs or A_front.
5. If values are normalized, include the normalization formula in comments or output metadata.

Performance checks:
If the code is slow, inspect in this order:
1. number of period points
2. mesh.nb_faces
3. whether 2D free-surface grids are inside the period loop
4. free-surface grid resolution
5. repeated unnecessary solver or mesh construction
6. repeated file export or plotting inside the loop

Code modification rules:
- Preserve existing output filenames unless there is a clear reason to change them.
- Add comments where formulas are defined.
- Prefer CSV outputs compatible with Origin.
- Keep model-specific outputs separated by N = 4, 6, and 8.
- Do not delete existing data files unless explicitly instructed.

Scientific caution:
- Do not overclaim “bandgap” unless the analysis actually supports attenuation or forbidden-propagation behaviour.
- Use “centre enhancement”, “local amplification”, “rear-field strengthening”, or “frequency-dependent scattering response” when the data only support those claims.
