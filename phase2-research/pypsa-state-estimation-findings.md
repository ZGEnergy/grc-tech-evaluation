# PyPSA State Estimation Investigation

## Summary

PyPSA has **no native state estimation (SE) capability** and there are **no known community
efforts** (issues, PRs, forks, or plugins) to add one. The PyPSA project explicitly
acknowledges SE as a missing feature relative to pandapower. However, PyPSA's numerical
building blocks (Newton-Raphson solver, sparse Jacobian construction, scipy/numpy linear
algebra) provide a plausible foundation for implementing WLS state estimation as a custom
extension. Two other Python-ecosystem tools -- pandapower and power-grid-model -- already
ship production-grade SE and could serve as references or interop targets.

## Native SE Support

**None.** PyPSA's feature set covers:

- Full nonlinear AC power flow (Newton-Raphson)
- Linearised DC power flow
- Linear, quadratic, and mixed-integer optimal power flow (via linopy)
- Multi-period investment and dispatch optimisation
- Contingency analysis (N-1)

The original PyPSA paper (Brown et al. 2018) and all subsequent documentation explicitly
position PyPSA as a power flow and optimisation tool. State estimation, short-circuit
analysis, and three-winding transformer modelling are listed as features present in
pandapower but absent from PyPSA.

## Community Efforts (Issues/PRs/Forks)

| Source | Search result |
|--------|--------------|
| GitHub Issues (`PyPSA/PyPSA`) | Zero issues matching "state estimation" |
| GitHub PRs (`PyPSA/PyPSA`) | Zero PRs matching "state estimation" |
| GitHub forks | No fork found adding SE functionality |
| PyPSA Google Group | No threads found on SE |
| GitHub Discussions | No discussions found on SE |
| PyPSA-Eur / PyPSA-USA / PyPSA-Earth | Regional model extensions; none add SE |
| GitHub `state-estimation` topic (Python) | Lists pandapower and power-grid-model; no PyPSA-based repo |

There is no evidence of any community member requesting, proposing, or implementing state
estimation within the PyPSA ecosystem.

## Academic Integration

No academic papers were found that combine PyPSA with state estimation. The literature
on Python-based power system SE consistently references:

- **pandapower** (Thurner et al. 2018) -- WLS SE with chi-squared and normalised residual
  bad-data detection
- **power-grid-model** (Alliander) -- iterative linear WLS SE with voltage phase angle
  correction across iterations
- Various standalone implementations (e.g., `nbhusal/Power-System-State-Estimation` on
  GitHub)

PyPSA appears exclusively in optimisation and planning literature, not in estimation or
monitoring contexts.

## Theoretical Feasibility

WLS state estimation is fundamentally a nonlinear least-squares optimisation problem:

    min_x  (z - h(x))^T W (z - h(x))

where z is the measurement vector, h(x) maps state to measurements, and W is the
inverse-covariance weight matrix. This is solved iteratively via the Gauss-Newton method,
which requires:

1. **Admittance matrix (Y-bus)** -- PyPSA builds this already for power flow.
2. **Jacobian of measurement functions** -- PyPSA builds a power-flow Jacobian
   (dP/dtheta, dP/dV, dQ/dtheta, dQ/dV) for Newton-Raphson. The SE Jacobian
   (dh/dx) is structurally similar but includes rows for voltage magnitude, line
   flow, and injection measurements rather than just bus power mismatches.
3. **Sparse linear solve** -- PyPSA uses scipy.sparse with UMFPACK (same solver
   as MATPOWER) for its Newton-Raphson iterations.
4. **Measurement model** -- Not present in PyPSA. Would need to be built: measurement
   types (P_inj, Q_inj, V_mag, P_flow, Q_flow), noise/weight specification,
   placement topology.

**What could be reused from PyPSA:**
- Network data model (buses, lines, transformers, generators, loads)
- Y-bus construction routines
- Sparse matrix infrastructure
- Newton-Raphson iteration scaffolding (convergence checks, iteration limits)

**What would need to be built from scratch:**
- Measurement data model (type, location, value, variance)
- SE-specific Jacobian (h(x) and dh/dx for each measurement type)
- WLS normal equations solver (gain matrix G = H^T W H)
- Bad-data detection (chi-squared test, largest normalised residual)
- Observability analysis (rank check of H matrix)
- Optional: PMU measurement handling, topology error detection

**Estimated effort:** Moderate. A basic WLS SE for bus injection and voltage measurements
could be prototyped in ~500-1000 lines of Python leveraging PyPSA's network model and
scipy.sparse. A production-quality implementation with all measurement types, bad-data
detection, and observability analysis would be significantly more work, and at that point
using pandapower's existing SE module or power-grid-model would be more practical.

**Linopy/optimisation path:** PyPSA's linopy-based optimiser supports quadratic
objectives (QP), so a WLS SE could theoretically be formulated as a QP. However, SE
requires nonlinear measurement equations h(x), making a pure LP/QP formulation
incomplete -- you would still need iterative linearisation, which is essentially
reimplementing Gauss-Newton. This path offers no real advantage over direct
implementation with scipy.

## Alternative Approaches for Phase 2

Given the absence of native SE in PyPSA, the Phase 2 evaluation has several options:

1. **Use pandapower for SE tasks** -- pandapower has mature WLS SE with bad-data
   detection. Networks can be converted between PyPSA and pandapower formats.
2. **Use power-grid-model** -- Alliander's C++-backed tool with Python bindings;
   fast iterative linear WLS SE. Designed for distribution grids but applicable
   to transmission.
3. **Build a minimal SE on PyPSA's network model** -- Feasible as a proof of concept
   but significant effort for a robust implementation.
4. **Acknowledge as a gap** -- Document that PyPSA does not support SE and evaluate
   this dimension using pandapower or PowerModels.jl instead.

## Sources

- [PyPSA: Python for Power System Analysis (Brown et al. 2018)](https://openresearchsoftware.metajnl.com/articles/10.5334/jors.188)
- [PyPSA GitHub repository](https://github.com/PyPSA/PyPSA)
- [PyPSA documentation](https://docs.pypsa.org/latest/)
- [PyPSA arXiv preprint](https://arxiv.org/abs/1707.09913)
- [pandapower paper (Thurner et al. 2018)](https://arxiv.org/pdf/1709.06743)
- [pandapower website](https://www.pandapower.org/)
- [power-grid-model documentation -- state estimation](https://power-grid-model.readthedocs.io/en/v1.5.14/user_manual/calculations.html)
- [GitHub state-estimation topic (Python)](https://github.com/topics/state-estimation?l=python)
- [Linopy GitHub repository](https://github.com/PyPSA/linopy)
- [PyPSA optimization with linopy example](https://docs.pypsa.org/v0.27.1/examples/optimization-with-linopy.html)
