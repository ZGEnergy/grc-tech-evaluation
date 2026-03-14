---
test_id: D-4
tool: pypsa
dimension: accessibility
network: TINY
status: pass
workaround_class: null
timestamp: 2026-03-13T12:00:00Z
protocol_version: v10
skill_version: v1
test_hash: 95535864
---

# D-4: Error Quality

## Summary

PyPSA produces meaningful diagnostics for 2 of 3 deliberate error scenarios. The
third error (missing cost curve) produces a clear exception, though the message
could be more specific. No errors fail silently.

## Error Test Results

### Error 1: Line limit set to 0 (infeasible OPF)

**Setup:** Single line with `s_nom=0` connecting a 100 MW generator to a 50 MW load.

**Result:** HiGHS detects infeasibility during presolve. PyPSA reports:
```
Status: warning
Termination condition: infeasible
```

**Diagnostic quality: GOOD.** The solver correctly identifies the problem as infeasible
during presolve (zero iterations). The status is `warning` rather than `ok`, and the
termination condition is `infeasible`. A user would immediately understand the problem.
The error is surfaced through linopy's standard reporting, not buried in solver logs.

### Error 2: Missing generator cost curve (marginal_cost omitted)

**Setup:** Two generators with no `marginal_cost` specified, connected to a 50 MW load.

**Result:** PyPSA raises:
```
ValueError: Objective function could not be created. Please make sure the
components have assigned costs.
```

**Diagnostic quality: GOOD.** The exception is raised before the solver is invoked,
with a clear message that identifies the root cause (missing costs). In PyPSA v1.1.2,
`marginal_cost` defaults to 0.0, but the optimizer requires at least one non-zero
cost term to construct a meaningful objective. The error message directly tells the
user what to fix.

Note: In older PyPSA versions, zero marginal cost was silently accepted and produced
a degenerate LP with non-unique optimal dispatch. The v1.1.2 behavior (explicit error)
is an improvement.

### Error 3: Invalid bus reference (generator assigned to nonexistent bus)

**Setup:** Generator with `bus='nonexistent_bus'` added to a network that only has
`bus0`.

**Result:** The `n.add()` call succeeds without error. The problem is caught at
`n.optimize()` time with:
```
ConsistencyError: The following generators have buses which are not defined.
Add them using n.add() or run n.sanitize() to add them automatically.
Components with undefined buses:
Index(['gen'], dtype='object', name='name')
```

**Diagnostic quality: GOOD.** The error identifies the exact component (`gen`) and
the nature of the problem (undefined bus). The suggestion to use `n.add()` or
`n.sanitize()` provides an actionable fix path. The only weakness is that the
error is deferred to solve time rather than caught at `n.add()` time -- a user
building a network interactively would not know about the invalid reference until
they attempt to solve.

### Supplementary: Invalid bus control type

**Setup:** Bus added with `control='InvalidType'`.

**Result:** No error raised. PyPSA accepts arbitrary control type strings without
validation. This is a minor gap -- invalid control types would manifest as incorrect
PF behavior rather than an error message.

## Cross-Reference to Observations

- **api-friction A-9:** The SCOPF API produces a clear error when transformer names
  are passed to `branch_outages`: "The following passive branches are not in the
  network: {('Line', 'T0'), ...}". The error message is technically accurate but
  does not explain the transformer exclusion limitation or suggest a workaround.

- **api-friction B-3:** `n.lpf_contingency()` is broken on Python 3.12+ and
  produces an opaque internal error rather than a version-compatibility diagnostic.

- **convergence-quality A-2:** ACPF convergence diagnostics (converged, n_iter,
  error) are first-class return values, making it easy to diagnose NR failures.

## Assessment

PyPSA's error reporting is generally good. Infeasibility is clearly reported through
the solver status. Missing costs produce an explicit ValueError. Invalid bus
references are caught with a ConsistencyError that names the offending components.
The main weakness is deferred validation -- component-level errors are caught at
solve time rather than at construction time, which can lead to confusing debugging
sessions when building networks incrementally.
