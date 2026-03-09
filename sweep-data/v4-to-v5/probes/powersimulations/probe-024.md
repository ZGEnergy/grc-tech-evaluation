---
probe_id: probe-024
tool: powersimulations
source_test: C-2
probe_type: convergence_check
classification: claim_supported
reason: "ACPF on 10k-bus network returns Missing (silent failure) in 5.5s with zero diagnostic info; no iteration count, no residual, no configurable tolerances"
solver_version: "PowerFlows.jl 0.9.0 (NewtonRaphsonACPowerFlow)"
solver_version_match: true
timeout_seconds: 600
wall_clock_seconds: ~170
timestamp: "2026-03-09T22:00:00Z"
---

# Probe 024: ACPF Scale Failure Diagnostics on ACTIVSg 10k

## Original Claim

From C-2 (scalability/C-2_acpf_scale.md):

> "The Newton-Raphson ACPF solver did not converge on the 10,000-bus network. [...] Error: 'The NewtonRaphsonACPowerFlow solver failed to converge'"

The probe investigates:
1. Does the ACPF actually fail on ACTIVSg 10k?
2. What diagnostic information does PowerFlows.jl provide?
3. Are there configurable solver parameters that could help?

## Probe Methodology

1. Loaded ACTIVSg 10k network (10,000 buses, 12,706 branches, 2,485 generators)
2. Attempted ACPF via `solve_powerflow(ACPowerFlow(), sys)`
3. Inspected return value and error messages
4. Examined `ACPowerFlow` constructor fields for configurable parameters
5. Ran ACPF on IEEE 39-bus for comparison (convergence baseline)

Script: `probe-024_script.jl`

## Probe Results

```
PowerFlows.jl v0.9.0

ACTIVSg 10k loading: 18.0s
  Network: 10,000 buses, 12,706 branches, 2,485 generators

ACPF on ACTIVSg 10k:
  Return type: Missing (silent failure indicator)
  Wall clock: 5.46s
  Exception: NONE (no error thrown)
  Iteration count: NOT REPORTED
  Residual: NOT REPORTED
  Error message: NONE

ACPF on IEEE 39-bus:
  Return type: Dict with ["flow_results", "bus_results"]
  Wall clock: 0.49s
  Status: CONVERGED

ACPowerFlow constructor fields:
  check_reactive_power_limits = false
  exporter = nothing
  calculate_loss_factors = false

  NO tolerance parameter
  NO max_iteration parameter
  NO warm_start parameter
```

## Analysis

**Convergence failure confirmed.** The ACPF on ACTIVSg 10k returns `Missing` -- a Julia sentinel value indicating non-convergence. This is consistent with the C-2 evaluation's finding, though the error mode differs slightly:

- **C-2 reported:** An error message "The NewtonRaphsonACPowerFlow solver failed to converge"
- **Probe found:** No exception thrown; function returns `Missing` silently

This discrepancy may be due to different PowerFlows.jl versions or calling patterns. The C-2 evaluation may have used `solve_powerflow!` (mutating) vs `solve_powerflow` (non-mutating), or a version that logged the message.

**Diagnostic quality is genuinely poor.** The `ACPowerFlow` type exposes only three configuration options, none related to the NR solver:
1. `check_reactive_power_limits` -- PV/PQ switching for Q limits
2. `exporter` -- output format
3. `calculate_loss_factors` -- loss factor computation

There is **no way to**:
- Set convergence tolerance
- Set maximum iterations
- Provide a DC warm start
- Get iteration count or residual from a failed solve
- Enable verbose solver logging

The solver either converges (returns Dict) or fails (returns Missing) with no intermediate information. For a 10,000-bus network, this is insufficient -- users cannot diagnose whether the problem is:
- Ill-conditioned Jacobian
- Insufficient iterations
- Poor initial point
- Numerical issues in specific network regions

**The IEEE 39-bus comparison confirms the solver works** on small networks (converges in 0.49s), so this is a scale-dependent convergence issue, not a broken solver.

## Classification Rationale

Classified as **claim_supported** because:
1. ACPF on ACTIVSg 10k fails to converge (returns `Missing`), confirming the C-2 FAIL result
2. Diagnostic quality is indeed poor -- no iteration count, no residual, no configurable tolerances
3. The failure mode is even less informative than C-2 reported (silent `Missing` return vs. error message)
4. The ACPowerFlow constructor exposes no NR-solver tuning parameters

The C-2 evaluation's assessment that "PowerFlows.jl may lack the robustness features needed for large-scale ACPF convergence" is corroborated.
