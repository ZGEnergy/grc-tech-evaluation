# MATPOWER State Estimation Investigation

## Summary

MATPOWER ships two separate state estimation (SE) implementations in its `extras/`
directory, both community-contributed and neither integrated with the modern MP-Core
(`mp.extension`) architecture introduced in MATPOWER 8. The newer `se/` package by
Rui Bo provides a classical Weighted Least Squares (WLS) estimator with observability
analysis and IEEE 14-bus test validation. The older `state_estimator/` by James S.
Thorp adds chi-squared bad data detection but is explicitly marked "under
construction." Neither module supports PMU measurements, robust estimation, or
large-scale network deployment. These are research/teaching tools, not
production-grade state estimators.

## SE Extras Overview

### `extras/se/` (mx-se, Rui Bo)

Master repository: [MATPOWER/mx-se](https://github.com/MATPOWER/mx-se), included
in `matpower-extras` as a git subrepo.

**Core functions:**

| Function | Purpose |
|---|---|
| `run_se(casename, measure, idx, sigma, type_initialguess, V0)` | Top-level entry point; loads case, builds admittance matrices, calls `doSE` |
| `doSE(baseMVA, bus, gen, branch, Ybus, Yf, Yt, V0, ref, pv, pq, measure, idx, sigma)` | WLS Newton iteration engine (max 100 iterations) |
| `isobservable(H, pv, pq)` | Rank-based observability test on the Jacobian H; diagnoses unobservable variables |
| `checkDataIntegrity(...)` | Validates measurement/index/sigma consistency |
| `getV0(...)` | Generates initial voltage profile (flat start or from power flow) |
| `outputsesoln(...)` | Formats and prints SE solution |

**Measurement types supported (8 categories):**
PF (branch active from), PT (branch active to), PG (generator active injection),
Va (voltage angle), QF (branch reactive from), QT (branch reactive to),
QG (generator reactive injection), Vm (voltage magnitude).

**Test cases:**
- `test_se` -- general validation
- `test_se_14bus` -- IEEE 14-bus system with 39 measurements across all categories
- `test_se_14bus_err` -- error handling validation
- `case3bus_P6_6.m` -- minimal 3-bus test case

**Documentation:** `se_intro.pdf` is included in the repository. No API reference
beyond MATLAB help text in function headers.

### `extras/state_estimator/` (James S. Thorp)

Older, simpler implementation bundled directly in matpower-extras.

**Core functions:**

| Function | Purpose |
|---|---|
| `runse(casedata, mpopt, fname, solvedcase)` | Runs Newton power flow first, then calls `state_est` |
| `state_est(branch, Ybus, Yf, Yt, Sbus, V0, ref, pv, pq, mpopt)` | WLS Newton estimator with chi-squared bad data detection (threshold 6.25) |

**Key difference from mx-se:** This module runs a full power flow *first*, then
uses the PF solution to generate synthetic measurements with added noise for
state estimation. It produces comparison plots (PF vs SE) for voltage angles,
magnitudes, and power flows. This is a teaching/demonstration tool.

## Algorithm Details

Both implementations use the same fundamental algorithm:

1. **Weighted Least Squares (WLS)** formulation:
   minimize `(z - h(x))^T W (z - h(x))` where `z` = measurements, `h(x)` =
   measurement model, `W` = diagonal weight matrix (`1/sigma^2`)

2. **Newton-Raphson iteration:** construct Jacobian `H = dh/dx`, solve the normal
   equation `(H^T W H) dx = H^T W (z - h(x))`, update state vector `x += dx`

3. **Convergence:** iterate until residual change is below tolerance or max
   iterations (100 for mx-se)

4. **Observability check (mx-se only):** rank test on H matrix before solving;
   if `rank(H) < n_states`, reports which variables lack measurement support

5. **Bad data detection (state_estimator only):** chi-squared test with threshold
   6.25; iteratively removes suspect measurements and re-solves

**Not supported by either module:**
- PMU / synchrophasor measurements (voltage/current phasors)
- Robust estimation (LAV, M-estimation, GM-estimation)
- Decoupled or fast-decoupled SE formulations
- Topology error detection
- Multi-area or distributed SE
- Real-time streaming measurement interfaces
- Sparse matrix optimizations for large networks

## Documentation & Examples

**mx-se (`extras/se/`):**
- `se_intro.pdf` provides a brief mathematical introduction
- MATLAB help text in each `.m` file with function signatures
- Three runnable test scripts serve as usage examples
- Reference docs hosted at matpower.org (e.g., [doSE](https://matpower.org/docs/ref/matpower5.0/extras/se/doSE.html),
  [run_se](https://matpower.org/docs/ref/matpower5.0/extras/se/run_se.html),
  [isobservable](https://matpower.org/docs/ref/matpower5.0/extras/se/isobservable.html))
- No tutorial, no user guide beyond the intro PDF
- No README in the mx-se repository

**state_estimator:**
- No dedicated documentation file
- MATLAB help text only
- `runse` generates comparison plots that serve as visual validation
- Referenced in [MATPOWER Extras appendix](https://matpower.app/manual/matpower/matpowerExtras.html)

**Documentation quality overall:** Minimal. Adequate for a researcher who already
understands WLS state estimation theory, but insufficient for a newcomer. No
step-by-step tutorials, no API design docs, no discussion of when to use which
module.

## Maintenance Status

### mx-se Repository

- **Created:** 2009 (initial commit from Rui Bo)
- **Total commits:** 19
- **Last commit:** 2019-06-07 (URL updates)
- **Last substantive code change:** 2018-04-05 (argument order fix for `dSbus_dV`)
- **Stars:** 10, Forks: 1
- **Open issues:** 3 (all filed 2024, none addressed):
  - #1: "Fix problem in state estimation"
  - #2: "add active & reactive load as measurements"
  - #3: "possible issue with computation of branch flow estimates"

The mx-se code has been **effectively dormant since 2019**. The three open issues
from 2024 suggest users are encountering bugs that are not being fixed.

### matpower-extras Repository

- **Latest release:** 8.1 (July 2025)
- **Total commits:** 255
- The `se/` subrepo has not been pulled/updated since at least 2019
- The `state_estimator/` code dates from the MATPOWER 5 era with no recent changes
- CI/CD workflows exist but focus on sdp_pf and other actively maintained extras

### Conclusion on Maintenance

Both SE modules are **legacy code in maintenance-only (or abandoned) status**.
They receive compatibility updates when MATPOWER core APIs change (e.g., the
2018 `dSbus_dV` argument reorder) but no feature development, no bug fixes for
reported issues, and no adaptation to MATPOWER 8's architecture.

## Integration Quality

### Relationship to MATPOWER Core

Both SE modules operate as **standalone scripts** that happen to use MATPOWER's
data structures and utility functions:

- They import case data via `loadcase()` and build admittance matrices via
  `makeYbus()` from MATPOWER core
- They use MATPOWER's bus/gen/branch matrix conventions and internal indexing
- They do NOT use `mp.extension`, `mp.task`, or any MP-Core class hierarchy
- They do NOT register as extensions or plug into MATPOWER's solve pipeline
- They cannot be invoked via `run_pf()`, `run_opf()`, or any standard entry point

### Legacy userfcn vs Modern mp.extension

The `state_estimator/runse` function uses MATPOWER's `runpf()` internally,
inheriting whatever power flow solver is configured. However, neither module
uses the `add_userfcn` callback API either -- they are truly standalone.

The modern `mp.extension` API (MATPOWER 8+) provides a clean path to integrate
SE as a first-class task type:
- A hypothetical `mp.task_se` could orchestrate data model -> network model ->
  math model for state estimation
- `mp.dm_element` subclasses could represent measurement devices
- `mp.mm_element` subclasses could formulate the WLS objective and constraints
- Extensions could add PMU elements, topology processing, or bad data detection

None of this integration exists. The SE extras remain at the MATPOWER 5-era
API level, requiring users to manually manage data flow between MATPOWER core
functions and the SE solver.

### What Would Full Integration Look Like?

A properly integrated SE module would:
1. Accept measurements as a data model layer alongside bus/gen/branch
2. Support `run_se('case14', measurements, mpopt)` as a top-level function
3. Use `mp.extension` to register SE-specific element types
4. Participate in MATPOWER's options system (`mpoption`)
5. Output results through MATPOWER's standard print/save pipeline
6. Be testable via MATPOWER's `t_run_tests` framework

Currently, none of these integration points are implemented.

## Production Readiness Assessment

| Criterion | mx-se (`extras/se/`) | state_estimator |
|---|---|---|
| Algorithm | WLS Newton-Raphson | WLS Newton-Raphson |
| Observability analysis | Yes (rank-based) | No |
| Bad data detection | No | Yes (chi-squared, basic) |
| PMU support | No | No |
| Scalable to large networks | No (dense matrices) | No (dense matrices) |
| Validated test cases | IEEE 14-bus, 3-bus | IEEE 9-bus (default) |
| Active maintenance | No (dormant since 2019) | No (dormant since ~2013) |
| Open bugs | 3 unaddressed | Unknown |
| Documentation | Minimal (intro PDF + help text) | Minimal (help text only) |
| MP-Core integration | None | None |
| Production deployable | No | No |

**Bottom line:** These SE extras are suitable for academic demonstrations and
small-network teaching exercises. They implement the textbook WLS algorithm
correctly for simple cases but lack the robustness, scalability, measurement
diversity, and maintenance commitment required for production or even serious
research use. For production-grade state estimation in MATLAB, users would need
to look at commercial tools (e.g., PSS/E, PowerWorld) or build a custom
implementation on top of MATPOWER's network model infrastructure.

For the evaluation context: the existence of SE extras demonstrates that
MATPOWER's data structures and admittance matrix utilities provide a viable
foundation for building SE tools, but the extras themselves are not evidence
of mature SE capability. They are better characterized as community-contributed
examples that have not kept pace with MATPOWER's architectural evolution.

## Sources

- [MATPOWER/mx-se GitHub repository](https://github.com/MATPOWER/mx-se) -- 19 commits, 3 open issues, last commit 2019
- [MATPOWER/matpower-extras GitHub repository](https://github.com/MATPOWER/matpower-extras) -- contributed/unsupported extras collection
- [MATPOWER Extras documentation](https://matpower.app/manual/matpower/matpowerExtras.html) -- official description of se and state_estimator modules
- [doSE function reference](https://matpower.org/docs/ref/matpower5.0/extras/se/doSE.html)
- [run_se function reference](https://matpower.org/docs/ref/matpower5.0/extras/se/run_se.html)
- [isobservable function reference](https://matpower.org/docs/ref/matpower5.0/extras/se/isobservable.html)
- [state_est function reference](https://matpower.org/docs/ref/matpower5.0/extras/state_estimator/state_est.html)
- [runse function reference](https://matpower.org/docs/ref/matpower5.0/extras/state_estimator/runse.html)
- [test_se_14bus function reference](https://matpower.org/docs/ref/matpower6.0/extras/se/test_se_14bus.html)
- [MATPOWER Extension API How-To](https://matpower.org/documentation/howto/extension.html) -- mp.extension class documentation
- [MATPOWER 8 Legacy Framework documentation](https://matpower.org/documentation/ref-manual/legacy/index.html)
- [MATPOWER 8.0 Release Notes](https://github.com/MATPOWER/matpower/blob/master/docs/relnotes/MATPOWER-Release-Notes-8.0.md)
