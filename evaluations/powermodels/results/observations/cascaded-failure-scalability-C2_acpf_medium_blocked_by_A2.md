---
tag: cascaded-failure
source_dimension: scalability
source_test: C-2
network: MEDIUM
tool: powermodels
severity: high
timestamp: 2026-03-11T08:00:00Z
---

# Cascaded Failure: C-2 ACPF Scale MEDIUM blocked by A-2 MEDIUM FAIL

## Observation

Test C-2 (ACPF Scale MEDIUM) fails as a direct cascaded failure from A-2 (ACPF MEDIUM, expressiveness dimension). The root capability — solving AC power flow on a 10,000-bus network using `compute_ac_pf` — was established as infeasible in A-2 MEDIUM. C-2 inherits this failure without requiring a separate re-execution.

### Chain:
- A-2 MEDIUM (expressiveness): FAIL — NLsolve Newton-Raphson does not converge on ACTIVSg10k after 21 minutes (both flat-start and DC warm-start exhausted)
- C-2 MEDIUM (scalability): FAIL — blocked by A-2 MEDIUM; same root cause, same measured timing

## Impact

- C-2 is blocked: `blocked_by: A-2`
- The scalability dimension cannot report a positive ACPF result at MEDIUM scale
- Scalability timing metrics (wall-clock per iteration, memory per bus, etc.) cannot be derived from a non-converging run
- The diagnostic gap (no NR iteration count, no residual from NLsolve) makes it impossible to characterize *how close* the solver came to convergence

## Distinction from A-2

A-2 tested ACPF as an expressiveness question: "Can the tool express and solve ACPF?" (Answer: no at MEDIUM scale).

C-2 tests ACPF as a scalability question: "What are the timing and memory characteristics at scale?" Since the solver does not converge, there are no valid scalability metrics to report.

## What Would Break the Cascaded Failure

If an Ipopt-backed ACPF path were implemented (e.g., using `instantiate_model` + `optimize_model!` with `ACPPowerModel` and fixed generation dispatch), both A-2 and C-2 could potentially pass. This would require:
1. Implementing a fixed-dispatch AC PF using the JuMP interface (not the standard `compute_ac_pf`)
2. Verifying that Ipopt converges on ACTIVSg10k with appropriate settings
3. Re-running timed measurements for both expressiveness and scalability grades

## Version

PowerModels.jl v0.21.5, Julia 1.10.
