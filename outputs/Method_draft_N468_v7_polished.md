## 2. Method

### 2.1 Numerical formulation

The hydrodynamic problem was solved using Capytaine (version 2.3.1), a Python-based frequency-domain linear potential-flow boundary element method (BEM) solver [Ancellin2019, CapytaineDoc]. Simulations were executed in Python 3.11.15. The governing assumptions follow linear potential-flow theory: incompressible, inviscid, and irrotational flow with a linearized free-surface boundary condition.

In the frequency domain, the velocity potential is written as
\[
\Phi(x,y,z,t)=\Re\left\{\phi(x,y,z;\omega)e^{-i\omega t}\right\}.
\]
Here, \(\omega\) is the angular frequency and \(g\) is the gravitational acceleration. The complex spatial potential \(\phi\) satisfies Laplace's equation in the fluid domain,
\[
\nabla^2 \phi = 0.
\]
At the still-water level \(z=0\), the linear free-surface boundary condition is
\[
\frac{\partial \phi}{\partial z}-\frac{\omega^2}{g}\phi=0
\quad \text{at } z=0.
\]
At the flat-bottom boundary \(z=-h\), the no-penetration condition is
\[
\frac{\partial \phi}{\partial z}=0
\quad \text{at } z=-h.
\]

For fixed-body diffraction, the total potential is decomposed as
\[
\phi=\phi_I+\phi_D.
\]
Here, \(\phi_I\) and \(\phi_D\) denote incident and diffracted components, respectively. On the wetted cylinder surface \(S_B\), with outward unit normal \(n\), the boundary condition is
\[
\frac{\partial \phi_D}{\partial n}=-\frac{\partial \phi_I}{\partial n}
\quad \text{on } S_B.
\]

The circular cylinders were fixed, and only the diffraction problem was solved. Body motion and radiation were excluded.

These equations define the continuous boundary-value problem solved by the BEM; the present study does not introduce an additional analytical multiple-scattering solution.

### 2.2 Geometry, meshing, and computational cases

All geometric and environmental quantities were defined in SI units. The cylinder radius was \(a = 0.06\,\mathrm{m}\), the water depth was \(h = 0.60\,\mathrm{m}\), and the ring radius was \(R = 0.30\,\mathrm{m}\). The cylinder draft (submerged length) was \(d = 0.598\,\mathrm{m}\), and the cylinder-center elevation was \(z_c = -d/2 = -0.299\,\mathrm{m}\). The array sizes were \(N=4\), \(N=6\), and \(N=8\), with cylinder centers uniformly distributed on a circle of radius \(R\).

The vertical coordinate convention was \(z=0\) at the still-water free surface and \(z<0\) in the submerged region. Under this convention, each cylinder extends approximately from \(z\approx 0\) to \(z\approx -0.598\,\mathrm{m}\). The cylinder radius, water depth, ring radius, and draft were kept constant across all cases, while the number of cylinders \(N\) was varied. This parameter variation modifies the azimuthal spacing, geometric openness, total wetted surface area, symmetry class, and multiple-scattering pathways.

Wetted surfaces were discretized with Capytaine `mesh_vertical_cylinder` at medium resolution \((n_r,n_\theta,n_z)=(16,16,6)\). This setup yielded 608 faces per cylinder. The final mesh sizes were 2432 faces for \(N=4\), 3648 faces for \(N=6\), and 4864 faces for \(N=8\).

### 2.3 Probe arrangement and response quantities

Seven fixed probes were used to extract free-surface responses in the frequency domain:

- Center-region probes:
  - \(P_0=(0.0,0.0)\)
  - \(P_1=(0.1,0.0)\)
  - \(P_2=(-0.1,0.0)\)
  - \(P_3=(0.0,0.1)\)
  - \(P_4=(0.0,-0.1)\)
- Axis probes:
  - \(\mathrm{front}=(-2.0,0.0)\)
  - \(\mathrm{rear}=(2.0,0.0)\)

Incident waves propagate from the front probe toward the rear probe along the positive \(x\)-direction.

For each period \(T\), the complex total free-surface response was defined as
\[
\eta_{\mathrm{total}} = \eta_{\mathrm{incident}} + \eta_{\mathrm{diffracted}}.
\]
The incident-amplitude-normalized response amplitude was
\[
A^*(x,y;T) = \frac{|\eta_{\mathrm{total}}(x,y;T)|}{A_{\mathrm{inc}}}.
\]
The incident-wave amplitude was set to unity in the post-processing outputs. Therefore, the exported quantity `total_abs` corresponds to the incident-amplitude-normalized modulus \(A^*\).

Based on \(A^*\), the following indicators were defined. The mean central response, \(A_{c,\mathrm{mean}}\), was
\[
A_{c,\mathrm{mean}} = \mathrm{mean}(A^*_{P_0},A^*_{P_1},A^*_{P_2},A^*_{P_3},A^*_{P_4}).
\]
The maximum central response, \(A_{c,\max}\), was
\[
A_{c,\max} = \max(A^*_{P_0},A^*_{P_1},A^*_{P_2},A^*_{P_3},A^*_{P_4}).
\]
The local nonuniformity ratio, \(R_{\mathrm{loc}}\), was
\[
R_{\mathrm{loc}} = \frac{A_{c,\max}}{A_{c,\mathrm{mean}}}.
\]
The front response \(A_{\mathrm{front}}\), rear response \(A_{\mathrm{rear}}\), and rear-to-front response ratio \(S_{\mathrm{rear/front}}\) were
\[
A_{\mathrm{front}}=A^*_{\mathrm{front}},\quad A_{\mathrm{rear}}=A^*_{\mathrm{rear}},\quad S_{\mathrm{rear/front}}=\frac{A_{\mathrm{rear}}}{A_{\mathrm{front}}}.
\]
`total_abs` is not a time-domain peak-to-peak wave height. It is a normalized complex-amplitude magnitude in the frequency domain. The quantity \(S_{\mathrm{rear/front}}\) is treated only as a rear-to-front point-response ratio and is not used as a wave-energy flux measure.

### 2.4 Frequency scan and post-processing

The period scan was defined as \(T=0.90\text{--}2.00\,\mathrm{s}\) with increment \(\Delta T=0.01\,\mathrm{s}\), giving 111 samples per array. The same period sequence, mesh level, probe layout, and post-processing definitions were used for \(N=4\), \(N=6\), and \(N=8\) to ensure methodological consistency.

For each array configuration, the computational workflow consisted of full-period diffraction solving, probe-wise extraction of complex free-surface responses, and standardized derivation of cross-period scalar indicators (\(A^*\), \(A_{c,\mathrm{mean}}\), \(A_{c,\max}\), \(R_{\mathrm{loc}}\), \(A_{\mathrm{front}}\), \(A_{\mathrm{rear}}\), and \(S_{\mathrm{rear/front}}\)). The resulting datasets were then assembled into single-array diagnostics and cross-array comparison summaries using identical definitions.

### 2.5 Boundary-peak handling and interpretation limits

Because the scan starts at \(T=0.90\,\mathrm{s}\), the interval \(T=0.90\text{--}0.93\,\mathrm{s}\) was treated as a near-boundary inspection interval to avoid over-interpreting peaks close to the lower scan limit. A peak located exactly at \(T=0.90\,\mathrm{s}\) or \(T=2.00\,\mathrm{s}\) is treated as a boundary peak and is not interpreted as a confirmed internal resonance peak. If a key conclusion depends on such a boundary peak, a refined short-period scan (e.g., \(T=0.85\text{--}1.05\,\mathrm{s}\) with \(\Delta T=0.005\,\mathrm{s}\)) is recommended to constrain boundary-peak uncertainty before final submission.
