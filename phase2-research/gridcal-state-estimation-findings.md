# GridCal State Estimation Investigation

## Summary

GridCal (now VeraGrid/VeraGridEngine) implements a WLS-based state estimation framework
with four solver algorithms, support for multiple measurement types, and nascent
observability analysis / pseudo-measurement augmentation. The implementation follows
Monticelli's textbook approach but has significant gaps: bad data detection is coded
but disabled, the decoupled solver has known issues, Issue #419 (observability +
pseudo-measurements) remains open with only a partial PR, and there is no time-series
SE driver. The feature is functional for small textbook-style grids but not
production-grade.

## Algorithm Details

The `StateEstimationDriver` class (in `state_stimation_driver.py` -- note the typo in
the filename) delegates to four WLS solver implementations in `state_estimation.py`:

| Solver | Function | Notes |
|--------|----------|-------|
| Newton-Raphson | `solve_se_nr()` | Solves (H'WH)^-1 H'W(z-h) directly; simplest impl |
| Levenberg-Marquardt | `solve_se_lm()` | Regularized (G'G + mu*I)dx = G'g with adaptive damping |
| Gauss-Newton | `solve_se_gauss_newton()` | Step-size limiting (+-0.3 rad angles, +-0.2 pu voltage) + regularization |
| Decoupled LU | `decoupled_state_estimation()` | P-theta / Q-V decoupling via `splu`; uses relaxed tolerance (100x tol) |

All solvers minimize `(z - h(x))' W (z - h(x))` where `W = diag(1/sigma^2)`.

**Measurement types supported:**
- Bus: P injection, Q injection, Vm, Va
- Generator: Pg, Qg
- Branch: Pf, Pt, Qf, Qt (from/to), If, It (current magnitude, handled as squared internally)

**Jacobian construction** (`Jacobian_SE` function): Uses `dSbus_dV_matpower`,
`dSbr_dV_matpower`, `dIbr_dV_matpower` to build the H matrix. Current measurements
use `d|I|^2 = 2*Re(diag(conj(I))*dI/dx)`.

**Configuration options** (`StateEstimationOptions`):
- `solver` (default NR), `tol` (1e-8), `max_iter` (100)
- `prefer_correct` vs deletion for bad data
- `c_threshold` (4.0) for bad data confidence
- `fixed_slack` -- must be False for convergence (documented in Issue #443)
- `run_observability_analyis`, `add_pseudo_measurements`, `pseudo_meas_std`
- `run_measurement_profiling`

**Reference:** Monticelli, "State Estimation in Electric Power Systems."

## Observability Analysis

Observability analysis is implemented as a two-phase approach in the driver:

1. `check_for_observability_and_return_unobservable_buses()` -- identifies unobservable
   buses and generates profiling data
2. `add_pseudo_measurements_for_unobservable_buses()` -- synthesizes measurements using
   linearized power flow equations when `add_pseudo_measurements=True`

**Current state:** The test file `test_observability_analysis_and_pseudo_meas.py` confirms
that the system can detect unobservable buses and that enabling pseudo-measurements
allows SE to converge on a 3-bus system. However, the test is incomplete:
- Multiple measurement definitions are commented out
- No validation of solution accuracy (only convergence checked)
- The test asserts unobservable buses remain flagged even after pseudo-measurements are
  added, which seems contradictory (possibly intentional for diagnostic tracking)

**Redundancy profiling:** Mentioned in Issue #419 requirements but not fully implemented.
The issue requests global and local redundancy mapping plus critical measurement
identification.

## Issue #419 Status

**Title:** [STATE-ESTIMATION] Observability analysis including redundancy information
for measurements & dealing with pseudo measurements

- **State:** OPEN (as of 2026-03-27)
- **Created:** 2025-08-25 by AnkurArohi (collaborator)
- **Last comment:** 2025-08-26

**What was requested:**
1. Observability analysis with measurement profiling (global/local redundancy, criticality)
2. Pseudo-measurement generation at locations critical for SE convergence using
   linearized power flow equations
3. Bad data identification and elimination with re-analysis

**What was delivered:**
A branch (`419_state_estimation_obsevability_analysis`) with a single commit adding a
3-bus test and pseudo-measurement feature. The comparison page shows only 2 files changed.
The branch has not been merged.

**Assessment:** The feature request is substantive (Monticelli/Abur textbook-level
capabilities) but the implementation effort appears minimal. The issue has been open for
7 months with no merge activity.

## Known Limitations

1. **Bad data detection disabled:** The b-test (Monticelli & Garcia 1983) is fully coded
   but commented out in all solvers. Users cannot detect or remove bad measurements
   automatically.

2. **Decoupled solver broken:** SanPen confirmed in Issue #443 that "all solvers pass
   [the 3-bus test] except the Decoupled_LU, which might ignore the `fixed_slack`
   setting."

3. **Unit scaling bugs (Issue #353, #443):** SE results were returned in per-unit while
   power flow results used MVA, causing 100x discrepancies. Issue #353 (fixed 2025-04-01)
   addressed input/output in MVA. Issue #443 (closed 2025-10-08) was a user confusion
   but revealed the Sbase handling is fragile -- the results writer is shared with
   power flow and "not consistently handled" per collaborator AnkurArohi.

4. **No time-series SE:** `get_measurements_and_deviations()` ignores the time parameter
   (`t=None` always). There is no `StateEstimationTimeSeriesDriver` equivalent.

5. **Current measurement handling:** Code supports both squared and direct magnitudes but
   defaults to squared. A comment notes direct approach is "more stable" but it is not
   the default.

6. **Critical measurements:** Flagged in code with "Do not delete" comment but not
   properly handled in the bad data pipeline.

7. **No PMU support:** Phase angle measurements (Va) are supported in the Jacobian but
   there is no dedicated PMU device model or linear SE formulation.

8. **Filename typo:** `state_stimation_driver.py` (missing 'e') -- minor but indicative
   of limited review.

9. **Observability + pseudo-measurements incomplete:** Issue #419 open, branch not merged,
   test is a stub.

10. **No multi-area SE:** Single-area estimation only; islands processed independently.

## Recent Development Activity

| Date | Event | Actor |
|------|-------|-------|
| 2025-03-31 | Issue #353 opened (MVA scaling) | SanPen |
| 2025-04-01 | Issue #353 closed | SanPen |
| 2025-08-25 | Issue #419 opened (observability + pseudo-meas) | AnkurArohi |
| 2025-08-26 | Branch with 3-bus test pushed for #419 | AnkurArohi |
| 2025-10-07 | Issue #443 opened (SE convergence/scaling) | Ferranbd (external) |
| 2025-10-08 | Issue #443 closed (user error, p.u. confusion) | SanPen |

**Development pattern:** SE work is sporadic. Most activity comes from collaborator
AnkurArohi, with SanPen providing direction. No SE-related commits found in recent
(late 2025 / early 2026) history. The #419 branch has stalled for 7 months.

**Bus factor concern:** SE development appears to depend on a single collaborator
(AnkurArohi) under the direction of the sole maintainer (SanPen). This compounds the
overall project bus factor of 1.

## Production Readiness Assessment

| Criterion | Status | Notes |
|-----------|--------|-------|
| Core WLS solver | Functional | NR, LM, GN work on textbook cases |
| Bad data detection | Not functional | Coded but commented out |
| Observability analysis | Partial | Detects unobservable buses; no redundancy profiling |
| Pseudo-measurements | Partial | Branch exists, not merged, minimal testing |
| Time-series SE | Missing | No driver exists |
| PMU/linear SE | Missing | No dedicated support |
| Decoupled solver | Broken | Fails tests per maintainer |
| Unit handling | Fragile | Fixed but shared code path with PF is a risk |
| Test coverage | Minimal | 3-bus textbook cases only |
| Documentation | Sparse | One-paragraph doc page + Monticelli reference |

**Overall:** GridCal's SE is a textbook-quality reference implementation suitable for
educational use and small proof-of-concept work. It is not production-ready for real
grid operations. The missing bad data detection alone disqualifies it -- SE without
bad data handling is unusable on real measurement sets. The stalled Issue #419 and
single-developer dependency add further risk.

## Sources

- [VeraGrid GitHub Repository](https://github.com/SanPen/VeraGrid)
- [Issue #419: Observability analysis + pseudo measurements](https://github.com/SanPen/VeraGrid/issues/419) (OPEN)
- [Issue #443: State Estimation scaling](https://github.com/SanPen/VeraGrid/issues/443) (CLOSED 2025-10-08)
- [Issue #353: SE powers in MVA](https://github.com/SanPen/VeraGrid/issues/353) (CLOSED 2025-04-01)
- [Issue #139: SE example does not run](https://github.com/SanPen/VeraGrid/issues/139) (CLOSED 2021-11-22)
- [SE source: state_estimation.py](https://github.com/SanPen/VeraGrid/blob/master/src/VeraGridEngine/Simulations/StateEstimation/state_estimation.py)
- [SE driver: state_stimation_driver.py](https://github.com/SanPen/VeraGrid/blob/master/src/VeraGridEngine/Simulations/StateEstimation/state_stimation_driver.py)
- [SE example: state_estimation_run.py](https://github.com/SanPen/VeraGrid/blob/master/examples/state_estimation_run.py)
- [SE test: test_observability_analysis_and_pseudo_meas.py](https://github.com/SanPen/VeraGrid/blob/master/src/tests/StateEstimation/test_observability_analysis_and_pseudo_meas.py)
- [VeraGrid State Estimation Documentation](https://veragrid.readthedocs.io/en/stable/)
- [GridCal SE Module Docs](https://gridcal.readthedocs.io/en/latest/_modules/GridCalEngine/Simulations/StateEstimation/state_estimation.html)
- Monticelli, A. "State Estimation in Electric Power Systems" (referenced in GridCal docs)
