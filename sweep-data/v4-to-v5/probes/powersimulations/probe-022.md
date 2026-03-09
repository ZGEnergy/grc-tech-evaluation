---
probe_id: probe-022
tool: powersimulations
source_test: B-1
probe_type: formulation_audit
classification: claim_supported
reason: "Binding flow gate constraint produces non-zero dual (-0.1398); dual extraction via JuMP.dual() works for both binding and non-binding cases"
solver_version: "HiGHS 1.21.1"
solver_version_match: true
timeout_seconds: 600
wall_clock_seconds: ~120
timestamp: "2026-03-09T21:00:00Z"
---

# Probe 022: Custom constraint binding dual extraction

## Original Claim

From B-1 (extensibility/B-1_custom_constraints.md):

> "Flow gate (binding test): Set gate limit to 80% of unconstrained absolute flow sum (8.33 pu). The signed flow sum was -5.54 pu, well below the limit, so the constraint was non-binding. Dual = 0.0 (correct for non-binding)."

The claim is that B-1 verified dual extraction only for the non-binding case (dual=0). A binding case with non-zero dual was never demonstrated, leaving it unclear whether PSI/JuMP can actually extract economically meaningful shadow prices from custom constraints.

## Probe Methodology

1. Loaded IEEE 39-bus network in PowerSystems.jl
2. Built DCOPF with PTDFPowerModel (same formulation as B-1)
3. Solved unconstrained baseline (objective = 22.7013)
4. Identified the same 3 gate lines used in B-1: bus-15-bus-16, bus-16-bus-17, bus-16-bus-19
5. Computed signed flow sum from unconstrained solve: -5.539 pu
6. Set a TIGHT limit at 50% of |signed sum| = 2.769 pu (guaranteed to bind)
7. Added constraint: -2.769 <= sum(gate_flows) <= 2.769
8. Re-solved and extracted dual via `JuMP.dual()`

Script: `probe-022_script.jl`

## Probe Results

```
Unconstrained objective: 22.7013
Constrained objective:   22.8417
Objective increase:       0.1404 (0.62%)

Gate flow sum (unconstrained): -5.539
Gate flow sum (constrained):   -2.769 (= limit, binding)

Lower constraint (-sum <= 2.769): dual = -0.13977, BINDING
Upper constraint (sum <= 2.769):  dual = 0.0, non-binding

Individual gate flows (constrained vs unconstrained):
  bus-16-bus-19: -2.144 vs -4.800
  bus-15-bus-16: -1.924 vs -3.178
  bus-16-bus-17:  1.298 vs  2.439
```

## Analysis

The probe successfully demonstrates what B-1 failed to show: a **binding** custom flow gate constraint with a **non-zero dual** value (-0.1398). Key findings:

1. **Dual extraction works for binding constraints.** `JuMP.dual()` returns the correct shadow price when the constraint is active. The dual of -0.1398 $/MWh means relaxing the gate limit by 1 pu would reduce cost by ~$0.14/h.

2. **The constraint materially affects dispatch.** Flow on bus-16-bus-19 dropped from -4.80 to -2.14 pu, and the objective increased by 0.62%, confirming the constraint is genuinely binding and economically meaningful.

3. **B-1's methodology was weak, not wrong.** The original evaluation chose a gate limit (80% of absolute flow sum = 8.33) that was far looser than the actual signed flow sum (-5.54), so the constraint never bound. The mechanism works correctly; the test design just missed the interesting case.

4. **The B-1 PASS grade is reasonable.** The test asks whether custom constraints + dual extraction work. They do. The gap was in test coverage (binding case), not in the tool's capability.

## Classification Rationale

Classified as **claim_supported** because the probe confirms that PSI's custom constraint + dual extraction mechanism works correctly for the binding case that B-1 did not test. The B-1 evaluation's claim that "the mechanism works correctly" and that "a tighter limit would produce a binding constraint with non-zero dual" is validated. The PASS grade stands.
