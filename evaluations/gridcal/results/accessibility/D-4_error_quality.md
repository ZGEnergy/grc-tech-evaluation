---
test_id: D-4
tool: gridcal
dimension: accessibility
network: TINY
protocol_version: "v11"
skill_version: v2
test_hash: "95535864"
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: null
solver: null
timestamp: "2026-03-24T12:00:00Z"
---

# D-4: Error Quality

## Result: INFORMATIONAL

## Finding

GridCal exhibits a strong asymmetry between power flow diagnostics (excellent) and
OPF diagnostics (poor). Deliberate errors in OPF produce no exceptions, warnings, or
infeasibility signals. The tool follows a "no exceptions, always return results"
philosophy that makes error detection dependent on manual result inspection.

## Evidence

Three deliberate errors were introduced and tested in devcontainer (measured 2026-03-24).

### Test (a): Infeasible OPF -- All Branch Thermal Limits Set to Zero

**Input:** All branch `rate` values set to 0.0 MW before running `linear_opf()`.

**Expected:** Solver reports infeasibility or warning about violated limits.

**Actual (measured):**
- `results.converged = True` -- no infeasibility detected
- Generator dispatch totals 6,254.23 MW (matching system load)
- `results.overloads` max: 1,040 MW (massive limit violations)
- `results.loading` max: 8.042e+22 (division by zero rating produces astronomical percentages)

**Error quality: POOR.** No exception, no warning, no infeasibility status. The soft
constraint formulation absorbs all limit violations into slack variables and reports
`converged=True`. A user checking only `results.converged` would believe the result is
valid. [tool-specific: soft-constraint OPF masks infeasibility]

### Test (b): Missing Generator Cost Curve -- All Costs Set to Zero

**Input:** All generator `Cost`, `Cost0`, and `Cost2` set to 0.0 before `linear_opf()`.

**Expected:** Warning about degenerate objective, or arbitrary feasible dispatch.

**Actual (measured):**
- `results.converged = True`
- Generator dispatch totals system load (feasible)
- No warning about zero-cost/degenerate objective

**Error quality: ACCEPTABLE.** Zero costs produce a degenerate LP where any feasible
dispatch is optimal. The solver correctly finds one. However, no diagnostic indicates
objective degeneracy, which could surprise a user who accidentally zeroed costs.

### Test (c): Invalid Bus Type -- No Slack Bus Designated

**Input:** All `bus.is_slack` set to `False` before Newton-Raphson power flow.

**Expected:** Error about missing reference bus, or convergence failure.

**Actual (measured):**
- `results.converged = True`
- `results.error = 1.211e-11` (excellent residual)
- `results.iterations = 4` (normal count)
- Voltage magnitudes differ from normal solve by max 4.760e-09 (negligible)

**Error quality: ACCEPTABLE BEHAVIOR, POOR DIAGNOSTICS.** The solver silently
auto-selects a slack bus, producing correct results. This is a reasonable engineering
default, but completely silent -- no log, warning, or result attribute indicates the
auto-assignment. A user testing distributed slack behavior would not know this happened.

### Diagnostic Quality Summary

| Test | Error Detected? | Diagnostic Quality | Classification |
|------|----------------|-------------------|----------------|
| (a) Infeasible OPF (rate=0) | No | Poor -- converged=True, must inspect overloads | [tool-specific] |
| (b) Zero costs | N/A (valid LP) | Acceptable -- correct but no degeneracy warning | [tool-specific] |
| (c) No slack bus | No | Acceptable behavior, silent auto-assignment | [tool-specific] |

### Cross-Reference: PF vs OPF Diagnostic Quality

Power flow diagnostics are excellent (from convergence-quality observation on A-2):
- `results.iterations` (int), `results.error` (float residual), `results.converged`
  (bool) are all first-class attributes
- NR convergence: 4 iterations, residual 3.32e-11 -- six orders below tolerance
- This achieves the highest convergence evidence tier (`residual_reported`)

OPF diagnostics are poor:
- Infeasible problems report `converged=True` [tool-specific: soft constraints]
- Silently ignored options produce no warnings (e.g., `distributed_slack` in OPF)
- Formulation issues (A-10 loss underestimation, A-12 battery sign behavior) produce
  results without validation checks

## Consumed Observations

- `convergence-quality-expressiveness-A-2_acpf`: Excellent PF diagnostics (residual_reported tier)
- `convergence-quality-scalability-C-5_ac_feasibility_progressive`: DCOPF->ACPF convergence failure on SMALL with no diagnostic to distinguish solver failure from AC-infeasible operating point
- `api-friction-expressiveness-A-11_distributed_slack_opf`: `distributed_slack` silently ignored by OPF
- `unit-mismatch-expressiveness-A-10_lossy_dcopf_lmp`: Loss formula produces 500x underestimate with no warning
- `api-friction-fnm_ingestion-G-FNM-1_fnm_ingestion_gate`: `open_file()` silently returns `None` for unsupported `.mat` format

## Implications

The PF/OPF diagnostic asymmetry is the central accessibility finding. Power flow
users get excellent convergence feedback. OPF users get no error signals at all --
infeasible problems "succeed," ignored options produce no warnings, and formulation
limitations produce silently wrong results. For a tool evaluation, this means OPF
results require manual validation at every step, significantly increasing the
expertise required for correct use.
