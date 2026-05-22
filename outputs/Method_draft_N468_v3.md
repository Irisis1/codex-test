## 2. Method

### 2.1 Numerical formulation

The hydrodynamic problem was solved using Capytaine (version 2.3.1), a Python-based frequency-domain linear potential-flow boundary element method (BEM) solver [Ancellin2019, CapytaineDoc]. The simulations were executed in Python 3.11.15. The governing assumptions follow standard linear potential-flow theory: the fluid is incompressible, inviscid, and irrotational, and the free-surface boundary condition is linearized. The circular-cylinder arrays are fixed, and only the diffraction problem is solved; body motions are constrained and radiation problems are not considered in this study. Multi-cylinder interactions are therefore treated within the framework of classical multiple-body water-wave interaction and scattering theory [KagemotoYue1986].

Previous studies have used fixed or truncated cylinder arrays to investigate wave-field manipulation phenomena, including cloaking- and concentration-related behaviors [Zhang2019_CloakedArrays, Zhang2020_InvisibilityConcentrator, Zhang2023_SPEC]. In the present work, these references are used only to position the numerical-method context. The present study is not formulated as an optimized cloaking device and does not claim invisibility or self-protected concentration.

### 2.2 Geometry and computational cases

All geometric and environmental quantities were defined in SI units. The cylinder radius was \(a = 0.06\,\mathrm{m}\), the water depth was \(h = 0.60\,\mathrm{m}\), and the ring radius was \(R = 0.30\,\mathrm{m}\). The cylinder draft (underwater length) was \(d = 0.598\,\mathrm{m}\), and the cylinder-center elevation was set as \(z_c = -d/2 = -0.299\,\mathrm{m}\). The array sizes considered were \(N=4\), \(N=6\), and \(N=8\), with cylinder centers evenly distributed on a circle of radius \(R\).

The vertical coordinate convention is defined explicitly as follows: \(z=0\) is the still-water free surface, and the submerged region is represented by \(z<0\). Under this convention, each cylinder extends approximately from \(z\approx 0\) to \(z\approx -0.598\,\mathrm{m}\). The cylinder radius, water depth, ring radius, and draft were kept constant across all cases, while changing \(N\) modifies the azimuthal discretization, opening ratio, total wetted surface area, array symmetry, and multiple-scattering paths.

The wetted surfaces were discretized using Capytaine's `mesh_vertical_cylinder` with the medium resolution \((n_r, n_\theta, n_z)=(16,16,6)\). For this resolution, the estimated panel count is
\[
N_{\mathrm{panel,cyl}} = (2n_r+n_z)n_\theta = (2\times16+6)\times16 = 608
\]
panels per cylinder, giving estimated total panel counts of 2432, 3648, and 4864 for \(N=4\), \(N=6\), and \(N=8\), respectively. These counts are estimated from the mesh-generation resolution and should be verified against `mesh.nb_faces` before final submission if exact mesh diagnostics are required.

### 2.3 Probe arrangement and response quantities

Seven fixed probes were used to extract the free-surface response in the frequency domain:

- Center-region probes:
  - \(P_0=(0.0,0.0)\)
  - \(P_1=(0.1,0.0)\)
  - \(P_2=(-0.1,0.0)\)
  - \(P_3=(0.0,0.1)\)
  - \(P_4=(0.0,-0.1)\)
- Axis probes:
  - \(\mathrm{front}=(-2.0,0.0)\)
  - \(\mathrm{rear}=(2.0,0.0)\)

The incident wave propagates from the front probe toward the rear probe along the positive \(x\)-direction (front \(\rightarrow\) array center \(\rightarrow\) rear).

For each period \(T\), the complex total free-surface response at a probe location is defined as
\[
\eta_{\mathrm{total}} = \eta_{\mathrm{incident}} + \eta_{\mathrm{diffracted}}.
\]
The incident-amplitude-normalized response amplitude is
\[
A^*(x,y;T) = \frac{|\eta_{\mathrm{total}}(x,y;T)|}{A_{\mathrm{inc}}}.
\]
In the exported point-probe data, `incident_abs = 1.0`; therefore `total_abs` corresponds to the incident-amplitude-normalized modulus of the complex total free-surface response.

Based on \(A^*\), the following scalar indicators were used:
\[
\mathrm{center\_mean\_abs} = \mathrm{mean}(A^*_{P_0},A^*_{P_1},A^*_{P_2},A^*_{P_3},A^*_{P_4}),
\]
\[
\mathrm{center\_max\_abs} = \max(A^*_{P_0},A^*_{P_1},A^*_{P_2},A^*_{P_3},A^*_{P_4}),
\]
\[
\mathrm{center\_max\_to\_mean\_ratio} = \frac{\mathrm{center\_max\_abs}}{\mathrm{center\_mean\_abs}}.
\]
Additionally,
\[
\mathrm{front\_abs}=A^*_{\mathrm{front}},\quad \mathrm{rear\_abs}=A^*_{\mathrm{rear}},\quad S_{\mathrm{rear/front}}=\frac{\mathrm{rear\_abs}}{\mathrm{front\_abs}}.
\]
Here, `total_abs` is a normalized complex-amplitude magnitude in the frequency domain, not a time-domain peak-to-peak wave height. The quantity \(S_{\mathrm{rear/front}}\) is used only as a rear-to-front response ratio and is not interpreted as an energy-based transmission coefficient.

### 2.4 Frequency scan and post-processing

The period scan was defined as \(T=0.90\text{--}2.00\,\mathrm{s}\) with increment \(\Delta T=0.01\,\mathrm{s}\), giving 111 period samples per array. The same period sequence, mesh level, probe layout, and post-processing definitions were applied to \(N=4\), \(N=6\), and \(N=8\) for methodological consistency.

The processing workflow is:

1. `run_ring_array.py` generates the full-scan CSV files for each array case.
2. `analyze_scan_results.py` and `plot_scan_diagnostics.py` generate single-array reports, anomaly checks, and diagnostic figures.
3. `compare_N4_N6_N8.py` generates cross-array comparison tables and figures.
4. `make_N468_5page_ppt.py` generates presentation slides only and is not part of the numerical method.

### 2.5 Boundary-peak treatment and interpretation limits

To reduce over-interpretation near scan boundaries, the interval \(0.90\text{--}0.93\,\mathrm{s}\) is marked as an anomaly-check interval. A peak located exactly at \(T=0.90\,\mathrm{s}\) or \(T=2.00\,\mathrm{s}\) is flagged as a boundary peak. Such boundary peaks are not interpreted as confirmed internal resonance peaks. If any conclusion depends materially on a boundary peak, a refined short-period scan (for example, \(T=0.85\text{--}1.05\,\mathrm{s}\) with \(\Delta T=0.005\,\mathrm{s}\)) should be considered before final submission.

### 2.6 Remaining checks before final submission

The remaining pre-submission checks are limited to the following two items:

1. Verify exact `mesh.nb_faces` values if exact panel numbers are required.
2. Consider short-period refinement if boundary-peak-based conclusions are retained.

### Internal citation notes

This section is for internal drafting only and should not be included in the submitted manuscript.

- **[Ancellin2019], [CapytaineDoc]**: Capytaine solver framework and implementation context.
- **[KagemotoYue1986]**: Classical multiple-body wave-interaction and scattering background.
- **[Zhang2019_CloakedArrays], [Zhang2020_InvisibilityConcentrator], [Zhang2023_SPEC]**: Prior fixed/truncated cylinder-array context for wave-field manipulation studies.
