# PowerModels.jl State Estimation Investigation

## Summary

PowerModels.jl core has **no native state estimation** capability. The primary SE package
in its ecosystem is **PowerModelsDistributionStateEstimation.jl (PMDSE)**, a third-party
extension built on PowerModelsDistribution.jl. It targets distribution networks only and
is a research-grade tool from KU Leuven with 5 contributors and a last release in Oct 2023.
A separate, unrelated Julia package -- **JuliaGrid.jl** -- provides transmission-focused
state estimation with WLS, LAV, PMU support, and bad data detection, but it is outside
the PowerModels ecosystem entirely. No `PowerModelsStateEstimation.jl` package exists for
transmission-level SE within the PowerModels family.

## PowerModelsDistributionStateEstimation.jl

Repository: <https://github.com/Electa-Git/PowerModelsDistributionStateEstimation.jl>

### Maturity Metrics

| Metric | Value |
|--------|-------|
| GitHub stars | 40 |
| Forks | 13 |
| Contributors | 5 |
| Open issues | 3 |
| License | BSD-3-Clause |
| Created | 2020-01-29 |
| Last commit | 2025-01-29 |
| Last release | v0.7.0 (2023-10-03) |
| Last push | 2025-02-07 |
| Language | Julia |
| Primary developers | Marta Vanin, Tom Van Acker (KU Leuven / Electa group) |

The package is academically maintained. The gap between the last tagged release (Oct 2023)
and ongoing commits (early 2025) suggests incremental maintenance without formal releases.
Five contributors and 30 commits in the default API page indicate a small, focused project.

### Algorithm Support

**Gaussian criteria:**

- **WLS** (Weighted Least Squares) -- Euclidean norm (p=2)
- **rWLS** (Relaxed WLS) -- second-order cone constraint formulation
- **WLAV** (Weighted Least Absolute Value) -- absolute value norm (p=1)
- **rWLAV** (Relaxed WLAV) -- exact linear relaxation with inequality constraints

**Non-Gaussian criteria:**

- **MLE** (Maximum Likelihood Estimation) -- connects residuals to log-pdf; supports
  non-normal distributions

**Supported measurement distributions:**

- Normal, Log-Normal, Exponential, Weibull, Gamma, Beta, Extended Beta
- Gaussian Mixture Models (GMM)
- Each measurement can use an individual criterion or a uniform criterion across all

**Power flow formulations for SE:**

- Exact: ACP, ACR, IVR (and reduced variants)
- Linear approximation: LinDist3Flow

### Transmission vs Distribution

PMDSE is **distribution-only**. It extends PowerModelsDistribution.jl (not PowerModels.jl),
which models unbalanced, multi-phase distribution networks. It cannot be applied to
balanced single-phase transmission models without significant modification. The package
explicitly describes itself as targeting "Power Distribution Network State Estimation."

There is no corresponding `PowerModelsStateEstimation.jl` for transmission networks in the
PowerModels ecosystem.

### Bad Data Detection

Three methods are implemented (added in v0.4.0):

1. **Chi-squared test** -- detection only (yes/no); compares weighted squared residual sum
   against chi-squared threshold; default false-positive probability 0.05
2. **Largest normalized residuals** -- detection and identification; threshold typically 3.0;
   flags specific measurements exceeding threshold
3. **LAV residual analysis** -- inherently robust to bad data; large residuals identify
   suspect measurements after estimation

All methods are **post-estimation** (require a completed SE run first). Chi-squared detects
presence but not location. Effectiveness varies by scenario.

### Known Limitations

- **Distribution only** -- no transmission network support
- **Research-focused** -- explicitly states the goal is not fastest algorithms but a
  benchmarking framework; "if faster solution times are crucial, a customized algorithm
  can be developed afterwards"
- **Small maintainer base** -- 5 contributors, primarily two lead developers
- **Release cadence slowing** -- last tagged release Oct 2023, though commits continue
- **No real-time / dynamic SE** -- static state estimation only
- **No PMU-specific algorithms** -- does not distinguish between SCADA and PMU measurement
  models in the way transmission SE tools do

## Other JuMP/PowerModels SE Packages

### JuliaGrid.jl

Repository: <https://github.com/mcosovic/JuliaGrid.jl>

| Metric | Value |
|--------|-------|
| GitHub stars | 48 |
| Forks | 5 |
| Contributors | 2 |
| License | MIT |
| Last push | 2026-02-06 |
| Created | 2020-04-07 |

JuliaGrid is an **independent** Julia framework (not part of the PowerModels ecosystem) that
provides comprehensive state estimation for **transmission networks**. It was the subject
of a 2025 academic paper (arXiv:2502.18229).

**SE capabilities:**

- Nonlinear SE (polar coordinates, legacy + PMU measurements)
- Linear SE (PMU-only, rectangular coordinates)
- DC state estimation (voltage angles only)
- WLS, LAV, and orthogonal WLS estimators
- Observability analysis
- Bad data detection via normalized residual tests
- Optimal PMU placement (integer LP via JuMP)

**JuMP integration:** Uses JuMP for OPF and LAV estimator formulations; compatible with
Ipopt and Gurobi solvers.

**Performance benchmarks (from 2025 paper):**

- 10,000-bus systems: competitive execution times
- 70,000-bus systems: handles 577,242 measurements; bad data analysis in ~1.2 seconds
- Comparable or superior ACPF times vs MATPOWER

**Limitations:** Only 2 contributors (essentially single-author). Distribution network
support is limited compared to transmission.

### PowerModelsStateEstimation.jl

**Does not exist.** No such package was found on GitHub, JuliaHub, or the Julia General
registry. The PowerModels ecosystem has no transmission-level SE extension.

### rosetta-opf

Repository: <https://github.com/lanl-ansi/rosetta-opf>

The ROSETTA project (by LANL-ANSI, same group behind PowerModels.jl) benchmarks AC-OPF
implementations across NLP modeling frameworks. It uses PowerModels.jl for data parsing
and PGLib-OPF benchmarks. **It has no state estimation component** -- it is purely an
OPF benchmarking effort.

## Production Readiness Assessment

| Criterion | PMDSE | JuliaGrid |
|-----------|-------|-----------|
| Scope | Distribution only | Transmission focused |
| Algorithm breadth | WLS, WLAV, MLE + relaxations | WLS, LAV, orthogonal WLS |
| Bad data detection | Yes (3 methods) | Yes (normalized residuals) |
| PMU support | No dedicated PMU model | Yes (dedicated linear SE) |
| Observability analysis | Not documented | Yes |
| Scale tested | Small distribution networks | Up to 70,000-bus |
| Maintainer base | 5 contributors (2 active) | 2 contributors (1 active) |
| Release maturity | v0.7.0, slowing cadence | v0.5.5, actively maintained |
| JuMP dependency | Yes (via PowerModelsDistribution) | Yes (for OPF and LAV) |
| Production use evidence | None found; research tool | None found; research tool |

**Neither package is production-ready for utility-scale state estimation.** Both are
academic/research tools. For the PowerModels ecosystem specifically, there is a clear gap:
no transmission-level SE package exists, and PMDSE is limited to distribution networks.
JuliaGrid partially fills the transmission SE gap but is outside the PowerModels family
and has an even smaller contributor base.

For production SE needs, commercial tools (e.g., PSS/E, PowerWorld, EMS/SCADA vendor
packages) or MATPOWER's SE module remain the practical choices.

## Sources

- [PowerModelsDistributionStateEstimation.jl - GitHub](https://github.com/Electa-Git/PowerModelsDistributionStateEstimation.jl)
- [PMDSE SE Criteria Documentation](https://electa-git.github.io/PowerModelsDistributionStateEstimation.jl/stable/se_criteria/)
- [PMDSE Bad Data Documentation](https://electa-git.github.io/PowerModelsDistributionStateEstimation.jl/v0.4/bad_data/)
- [PMDSE Power Flow Formulations](https://electa-git.github.io/PowerModelsDistributionStateEstimation.jl/stable/formulations/)
- [JuliaGrid.jl - GitHub](https://github.com/mcosovic/JuliaGrid.jl)
- [JuliaGrid.jl Documentation](https://mcosovic.github.io/JuliaGrid.jl/stable/)
- [JuliaGrid: An Open-Source Julia-Based Framework for Power System SE (arXiv 2025)](https://arxiv.org/html/2502.18229v1)
- [PowerModels.jl - GitHub](https://github.com/lanl-ansi/PowerModels.jl)
- [rosetta-opf - GitHub](https://github.com/lanl-ansi/rosetta-opf)
- [PowerModelsDistribution.jl - GitHub](https://github.com/lanl-ansi/PowerModelsDistribution.jl)
