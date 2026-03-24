---
probe_id: probe-005
tool: gridcal
source_test: A-3
probe_type: formulation_audit
classification: confirmed_issue
reason: >
  GridCal's linear_opf uses soft branch flow constraints (slack variables
  flow_slacks_pos / flow_slacks_neg in the LP). Branch 2_3_1 exceeds its
  derated limit (103.5%, 362 MW vs 350 MW limit) in the optimal solution,
  which is only possible with soft constraints. The A-3 'pass' verdict is
  misleading: a standard DCOPF requires hard flow limits. This is a
  formulation deficiency, not a pass.
solver: HiGHS
solver_version: "bundled with VeraGridEngine 5.6.28"
solver_version_match: true
tool_version: "VeraGridEngine 5.6.28"
timeout_seconds: 300
wall_clock_seconds: 2.1
timestamp: "2026-03-14T00:00:00Z"
---

# Probe 005: GridCal DC OPF Branch Constraint Formulation

## Claim Under Investigation

A-3 reports "pass" despite branch 2_3_1 showing 112% loading (103.5% in
probe re-run with consistent cost assignment). The concern is whether GridCal
enforces branch flow limits as hard constraints (standard DCOPF) or soft
constraints (slack variables).

## Finding: SOFT CONSTRAINTS CONFIRMED

### Source Code Evidence

Inspecting `VeraGridEngine/Simulations/OPF/opf_driver.py`:

```python
# Line 170-171 of opf_driver.py
self.results.overloads = (opf_vars.branch_vars.flow_slacks_pos[0, :]
                          - opf_vars.branch_vars.flow_slacks_neg[0, :])
```

The LP model contains explicit slack variables `flow_slacks_pos` and
`flow_slacks_neg` per branch. These are the textbook soft-constraint
formulation: the objective penalizes overloads rather than making them
infeasible. The `overloads` result field is the net slack magnitude.

### Runtime Evidence

Probe re-run (VeraGridEngine 5.6.28, IEEE 39-bus with 70% branch derating):

| Branch   | Loading | Flow (MW) | Derated Limit (MW) | Overload slack |
|----------|---------|-----------|-------------------|----------------|
| 2_3_1    | 103.5%  | 362.22    | 350.00            | -12.22 MW      |
| 16_19_1  | 100.0%  | -420.00   | 420.00            | 0 (at limit)   |

The `opf_results.overloads` array has a non-zero entry (-12.22 MW) at
branch index 2 (2_3_1), confirming the slack variable absorbed the
infeasibility rather than the solver rejecting the solution.

The result object exposes `contingency_flows_slacks_list` as an additional
attribute, further confirming a slack-based formulation is used throughout.

### Keyword Audit

- `opf_driver.py` contains keyword "slack": 2 hits, "overload": 7 hits
- `linear_opf` source: no hard flow constraint keywords found
- `OptimalPowerFlowOptions`: no settings for constraint hardness found

## Impact on A-3 Verdict

The A-3 pass condition checked:
1. Convergence (satisfied — trivially true with soft constraints)
2. LMPs extractable (satisfied)
3. At least 2 binding branches (satisfied — 6 branches at ≥99%)

None of the pass conditions test whether flow limits are enforced as hard
constraints. A correct DCOPF pass condition should verify:

```
max_loading <= 1.0 + epsilon
```

With that criterion, A-3 **fails**: branch 2_3_1 reaches 103.5%.

## Classification Rationale

This is a **confirmed_issue** (not a formulation_difference):

- Standard DCOPF is universally defined with hard flow constraints
- GridCal's soft-constraint variant allows infeasible physical solutions
- The 112%/103.5% overload is not a numerical artifact — it is the
  optimizer's deliberate choice to violate the limit at a penalty cost
- LMPs from a soft-constraint OPF are economically meaningful only if the
  penalty cost equals the true marginal cost of overload relief; this is
  unlikely to be calibrated correctly in GridCal's default configuration
- The `overloads_cost` attribute exists but was not set to non-trivial values
  in the default options

## Recommendation

The A-3 result should be reclassified as **partial_pass** or **fail** with
a note that GridCal's linear_opf uses soft branch flow constraints. This
is a significant expressiveness limitation for users who require strict
thermal limit enforcement.
