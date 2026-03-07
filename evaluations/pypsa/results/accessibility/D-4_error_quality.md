---
test_id: D-4
tool: pypsa
dimension: accessibility
network: N/A
protocol_version: "v4"
status: qualified_pass
workaround_class: null
wall_clock_seconds: null
peak_memory_mb: null
loc: null
solver: highs
timestamp: 2026-03-06T00:00:00Z
---

# D-4: Error Quality

## Objective

Evaluate the quality and actionability of error messages when users make common
mistakes.

## Test (a): Infeasible OPF -- Line capacity set to zero

**Setup**: 2-bus network, generator on bus 1, load on bus 2, connecting line with
`s_nom=0` (zero capacity).

**Observed behavior**: The solver (HiGHS) returns status `Infeasible` and PyPSA
reports:

```
Status: warning
Termination condition: infeasible
Solution: 0 primals, 0 duals
Objective: nan
```

The Python return value is `('warning', 'infeasible')`.

**Assessment**: GOOD. The infeasibility is clearly reported with an unambiguous
termination condition. The `nan` objective and zero solution counts make the
failure obvious. However, PyPSA does not provide diagnostic guidance about
*which* constraint is infeasible -- users must inspect the model manually or use
`compute_infeasibilities=True` (an optimize parameter) to identify the binding
constraint. The HiGHS solver detects infeasibility during presolve, so no
detailed infeasibility report is generated.

**Grade**: B+. Clear status, but no root-cause guidance.

## Test (b): Missing marginal cost

**Setup**: 2-bus network with 2 generators, both without `marginal_cost`.

**Observed behavior**: PyPSA raises a `ValueError` before solving:

```
ValueError: Objective function could not be created. Please make sure the
components have assigned costs.
```

**Assessment**: EXCELLENT. The error is caught at model-creation time (before
invoking the solver), the message is specific, and the remedy ("make sure the
components have assigned costs") is actionable. This is a well-designed
validation gate.

**Grade**: A. Clear, early, actionable error.

## Test (c): Invalid bus control type

**Setup**: `n.add('Bus', 'bad', control='InvalidType')`

**Observed behavior**: No error raised. The bus is created with
`control='InvalidType'` stored as-is. No validation occurs at add-time.

```python
>>> n.buses.loc["bad", "control"]
'InvalidType'
```

**Assessment**: POOR. PyPSA silently accepts an invalid enum value for the
`control` field. The `control` parameter should be one of `PQ`, `PV`, or
`Slack`, but no validation enforces this. The invalid value would only surface
later as a cryptic error during power flow (or be silently ignored during OPF).
This is a missing input validation gap.

**Grade**: D. Silent acceptance of invalid input.

## Summary

| Error Scenario | Detection | Message Quality | Actionability | Grade |
|---------------|-----------|----------------|---------------|-------|
| Infeasible OPF | At solve | Clear status | No root cause | B+ |
| Missing cost | Pre-solve | Specific + actionable | High | A |
| Invalid bus type | Never | No error | None | D |

## Verdict

**QUALIFIED PASS.** Two of three error scenarios produce clear, useful
diagnostics. The missing-cost validation is exemplary -- early detection with an
actionable message. Infeasibility reporting is adequate but lacks root-cause
analysis by default. The silent acceptance of invalid enum values is a
significant gap in input validation that could lead to hard-to-debug downstream
failures.
