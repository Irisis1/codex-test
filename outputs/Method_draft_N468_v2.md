## 2. Method

### 2.1 Numerical model and theoretical assumptions

The hydrodynamic problem was solved using Capytaine, a Python-based frequency-domain linear potential-flow BEM solver [Ancellin2019, CapytaineDoc]. The problem is formulated under linear potential-flow assumptions: incompressible, inviscid and irrotational flow, with a linearized free-surface condition. The cylinder arrays are fixed. Only the diffraction problem is considered. Body motions and radiation problems are not included. The multi-cylinder interaction problem is related to classical linear water-wave interaction theory for multiple three-dimensional bodies [KagemotoYue1986].

Fixed and truncated cylinder arrays have been used in previous water-wave cloaking and concentration studies [Zhang2019_CloakedArrays, Zhang2020_InvisibilityConcentrator, Zhang2023_SPEC]. However, the present study does not design an optimized cloaking device and does not claim invisibility or self-protected concentration.

### 2.2 Array geometry and parameter settings

The geometric and environmental parameters were defined in SI units:

- Cylinder radius: \(a = 0.06\) m
- Water depth: \(h = 0.60\) m
- Ring radius: \(R = 0.30\) m
- Underwater length (draft): \(d \approx 0.598\) m
- Cylinder center depth: \(z \approx -0.30\) m
- Array sizes: \(N = 4, 6, 8\)

The cylinder radius, water depth, ring radius and draft were kept constant, while changing \(N\) modifies the azimuthal discretization, opening ratio, total wetted surface area, array symmetry and multiple-scattering paths.

### 2.3 Probe layout

Seven fixed probes were used for frequency-domain free-surface response extraction:

- Center-region probes:
  - \(P_0 = (0.0, 0.0)\)
  - \(P_1 = (0.1, 0.0)\)
  - \(P_2 = (-0.1, 0.0)\)
  - \(P_3 = (0.0, 0.1)\)
  - \(P_4 = (0.0, -0.1)\)
- Far probes on the incident/scattering axis:
  - front = \((-2.0, 0.0)\)
  - rear = \((2.0, 0.0)\)

The incident-wave direction is defined as: front \(\rightarrow\) array center \(\rightarrow\) rear.

### 2.4 Response indicators

At each period sample, the following scalar indicators were computed from complex frequency-domain outputs:

- `total_abs`: modulus of the complex frequency-domain total free-surface response.
- Total response decomposition: total response = incident component + diffracted component.
- Since `incident_abs = 1.0` in the point-probe CSV files, all free-surface response amplitudes are described as normalized by the incident-wave amplitude.
- `center_mean_abs`: mean `total_abs` over \(P_0\)–\(P_4\).
- `center_max_abs`: maximum `total_abs` over \(P_0\)–\(P_4\).
- `center_max_to_mean_ratio`: `center_max_abs / center_mean_abs`.
- `front_abs`: `total_abs` at the front probe.
- `rear_abs`: `total_abs` at the rear probe.
- `S_rear_front`: `rear_abs / front_abs`.

To avoid interpretation ambiguity, `total_abs` is treated as a normalized complex-amplitude magnitude in the frequency domain, not a time-domain peak-to-peak wave height. `S_rear_front` is used only as a transmission-like indicator and is not treated as a strict transmission coefficient.

### 2.5 Frequency scan and post-processing workflow

The scan settings were:

- Period range: \(T = 0.90\)–\(2.00\) s
- Period increment: \(\Delta T = 0.01\) s
- Total samples: 111 periods per array
- Mesh level: medium mesh

The workflow is organized as follows:

1. `run_ring_array.py` generates full period-scan CSV files.
2. `analyze_scan_results.py` and `plot_scan_diagnostics.py` generate single-array reports, anomaly checks and diagnostic figures.
3. `compare_N4_N6_N8.py` generates cross-array comparison tables and figures.
4. `make_N468_5page_ppt.py` generates the 5-page summary PPT; this PPT output is presentation material and is not part of the numerical method itself.

### 2.6 Boundary-peak handling and interpretation limits

For quality control and conservative interpretation:

- The short-period interval 0.90–0.93 s is marked as an anomaly-check interval.
- A peak located at \(T = 0.90\) s or \(T = 2.00\) s is flagged as a boundary peak.
- Boundary peaks are not interpreted as confirmed internal resonance peaks.

### 2.7 Items to be confirmed before submission

The following items remain to be explicitly verified before final submission:

- Exact panel number / mesh resolution corresponding to the medium mesh.
- Coordinate-system convention for the \(z\)-direction.
- Whether additional short-period refinement \(T = 0.85\)–\(1.05\) s with \(\Delta T = 0.005\) s is required before final submission.

**TODO (pre-submission confirmation):**
- Confirm exact panel number / mesh resolution of medium mesh.
- Confirm coordinate-system convention for \(z\)-direction.

### 2.8 References and citation roles

- **[Ancellin2019]**: supports the statement that Capytaine is a Python-based frequency-domain linear potential-flow BEM solver.
- **[CapytaineDoc]**: supports Capytaine implementation/documentation details for the same solver framework.
- **[KagemotoYue1986]**: supports the theoretical background of multi-body linear water-wave interaction, multiple scattering and diffraction interaction.
- **[Zhang2019_CloakedArrays]**: supports prior use of fixed/truncated cylinder arrays for water-wave cloaking-related studies, including free-surface elevation, wave drift force and wave-direction effects.
- **[Zhang2020_InvisibilityConcentrator]**: supports prior ring-type truncated-cylinder studies on water-wave concentration and invisibility-related scattering manipulation.
- **[Zhang2023_SPEC]**: supports follow-up research context involving self-protected energy concentrator concepts, frequency-band behavior and nonlinear limitations.

These references are used only to position the methodological background and literature context. Their specific cloaking/invisibility/self-protected-concentrator conclusions are not directly transferred as claims for the present model.
