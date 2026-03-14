---
test_id: D-4
tool: gridcal
dimension: accessibility
network: "case39"
status: informational
workaround_class: null
protocol_version: "v10"
skill_version: v1
test_hash: "95535864"
timestamp: "2026-03-13T18:00:00Z"
---

# D-4: Error Quality

Three deliberate errors were introduced to assess diagnostic quality.

## Test (a): Infeasible OPF — All Branch Thermal Limits Set to Zero

**Input:** All branch `rate` values set to 0.0 MW before running `linear_opf()`.

**Expected behavior:** Solver reports infeasibility or at minimum a warning that all
branch limits are violated.

**Actual behavior:**
- `results.converged = True` — no infeasibility detected
- Generator dispatch is computed and totals 6,255 MW (matching system load)
- `results.overloads` array contains large non-zero values (up to 1,040 MW) indicating
  massive limit violations
- `results.loading` array contains values on the order of 1e22 (loading percentage
  becomes effectively infinite when rating is zero — division by zero produces
  astronomical percentages)

**Assessment:** The solver does not detect or report the infeasibility. Instead it
treats zero-rated branches as soft constraints via the overload slack variables and
produces a feasible dispatch that violates all branch limits. The `converged = True`
status is misleading. The `loading` values (1e22) are numerically absurd but no
warning or error is raised. A user checking only `results.converged` would believe
the result is valid.

**Error quality grade:** Poor. No exception, no warning, no infeasibility status.
The user must manually inspect `overloads` and `loading` arrays to detect the problem.

## Test (b): Missing Generator Costs — All Costs Set to Zero

**Input:** All generator `Cost`, `Cost0`, and `Cost2` set to 0.0 before running
`linear_opf()`.

**Expected behavior:** Solver either warns about degenerate objective function or
produces an arbitrary feasible dispatch (since all generators are equally cheap).

**Actual behavior:**
- `results.converged = True`
- Generator dispatch totals to system load (feasible)
- Dispatch is arbitrary among generators (no cost-based ordering since all costs are 0)
- No warning about zero-cost objective

**Assessment:** Acceptable behavior. Zero costs produce a degenerate LP where any
feasible dispatch is optimal. The solver correctly finds one such dispatch. However,
no diagnostic indicates that the objective is degenerate, which could surprise a user
who accidentally zeroed costs. A warning would be helpful but the silent behavior is
not incorrect.

**Error quality grade:** Acceptable. Solver behavior is mathematically correct.

## Test (c): No Slack Bus — All `is_slack` Set to False

**Input:** All bus `is_slack` attributes set to `False` before running Newton-Raphson
power flow.

**Expected behavior:** Solver fails to converge or raises an error about missing
reference bus.

**Actual behavior:**
- `results.converged = True`
- `results.error = 1.21e-11` (excellent residual)
- `results.iterations = 4` (normal iteration count)
- Voltage magnitudes are identical to the normal solve (max difference = 0.000000)

**Assessment:** The solver silently auto-selects a slack bus when none is designated.
The result is numerically identical to the normal case (where bus 39 is slack). This
is a reasonable engineering default — many tools auto-assign a slack bus — but it is
completely silent. No log message, warning, or result attribute indicates that the
slack bus was auto-assigned. A user who intentionally removes all slack buses (e.g.,
to test distributed slack behavior) would not know this happened.

**Error quality grade:** Acceptable behavior, poor diagnostics. The auto-assignment
is reasonable but the lack of any notification is a usability gap.

## Consumed Observations

- `convergence-quality-expressiveness-A-2_acpf`: Positive finding — excellent
  convergence diagnostics (iteration count, residual, converged flag) directly on
  results object for power flow.
- `solver-issues-expressiveness-A-10_lossy_dcopf_lmp`: `add_losses_approximation`
  parameter produces negligible losses with no warning about accuracy.
- `solver-issues-expressiveness-A-12_multiperiod_dcopf_storage`: Battery energy balance
  sign error produces incorrect results silently (no warning, no validation check).
- `api-friction-expressiveness-A-11_distributed_slack_opf`: `distributed_slack` flag
  silently ignored by OPF — no warning that the option has no effect.

## Summary

| Test | Error Detected? | Diagnostic Quality |
|------|----------------|-------------------|
| (a) Infeasible OPF (rate=0) | No | Poor — converged=True, must inspect overloads manually |
| (b) Zero costs | N/A (valid LP) | Acceptable — correct but no degeneracy warning |
| (c) No slack bus | No | Acceptable behavior, silent auto-assignment |

GridCal's error reporting follows a "no exceptions, always return results" philosophy.
Power flow diagnostics (iteration count, residual, converged flag) are excellent
(per A-2 observation). However, OPF diagnostics are weak: infeasible problems report
converged=True, silently ignored options produce no warnings, and formulation bugs
(A-12 battery sign error) produce incorrect results without any validation check.
The asymmetry between power flow diagnostic quality and OPF diagnostic quality is
notable.
