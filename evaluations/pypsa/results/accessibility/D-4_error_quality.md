---
test_id: D-4
tool: pypsa
dimension: accessibility
network: N/A
protocol_version: v11
skill_version: v2
test_hash: 95535864
status: pass
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
timestamp: 2026-03-24T18:30:00Z
---

# D-4: Error Quality

## Result: PASS

## Finding

PyPSA produces meaningful diagnostics for all 3 deliberate error scenarios.
No errors fail silently. Error messages identify the root cause and, in 2 of 3
cases, suggest corrective action.

## Evidence

### Error 1: Infeasible OPF (line limit = 0)

**Setup:** Single line with `s_nom=0` connecting a 100 MW generator to a 50 MW load.

**Result:** HiGHS detects infeasibility during presolve:
```
Model status        : Infeasible
Status: warning
Termination condition: infeasible
Solution: 0 primals, 0 duals
```

**Classification: Meaningful diagnostic.** The solver correctly identifies the
problem as infeasible during presolve (zero iterations). The `optimize()` return
value is `('warning', 'infeasible')`, which a user can programmatically check.
The infeasibility is surfaced through linopy's standard reporting. [tool-specific]

### Error 2: Missing generator cost (marginal_cost omitted)

**Setup:** Two generators with no `marginal_cost` specified, connected to a 50 MW load.

**Result:** PyPSA raises before invoking the solver:
```
ValueError: Objective function could not be created. Please make sure the
components have assigned costs.
```

**Classification: Meaningful diagnostic.** The exception is raised before solve
time with a clear message identifying the root cause (missing costs) and
suggesting the fix (assign costs). In PyPSA v1.1.2, `marginal_cost` defaults to
0.0 for all generators, so this error fires when ALL generators have zero cost,
producing an empty objective. [tool-specific]

### Error 3: Invalid bus reference (generator on nonexistent bus)

**Setup:** Generator with `bus='nonexistent_bus'` added to a network with only `bus0`.

**Result:** The `n.add()` call succeeds silently. Error is caught at `n.optimize()` time:
```
ConsistencyError: The following generators have buses which are not defined.
Add them using n.add() or run n.sanitize() to add them automatically.
Components with undefined buses:
Index(['gen0'], dtype='object', name='name')
```

**Classification: Meaningful diagnostic.** The error names the offending component
(`gen0`) and suggests two corrective actions (`n.add()` or `n.sanitize()`). The
only weakness is deferred validation -- the invalid bus reference is accepted at
`n.add()` time and caught only at solve time, which can lead to confusing
debugging sessions when building networks incrementally. [tool-specific]

### Summary Table

| Error Scenario | Classification | Timing | Actionable? |
|---------------|---------------|--------|-------------|
| Infeasible OPF (s_nom=0) | Meaningful diagnostic | At solve | Yes (status tuple) |
| Missing generator cost | Meaningful diagnostic | Pre-solve | Yes (exception + message) |
| Invalid bus reference | Meaningful diagnostic | At solve (deferred) | Yes (names component + fix) |

### Cross-Reference to Observations

- **[api-friction A-9](../observations/api-friction-expressiveness-A-9_scopf.md):**
  SCOPF API produces a clear error when transformer names are passed to
  `branch_outages`, but does not explain the transformer exclusion limitation.
- **[convergence-quality A-2](../observations/convergence-quality-expressiveness-A-2_acpf.md):**
  ACPF convergence diagnostics (`converged`, `n_iter`, `error`) are first-class
  return values, making NR failure diagnosis straightforward.

## Implications

PyPSA's error reporting is strong. All three test scenarios produce meaningful
diagnostics that identify the root cause and suggest fixes. The deferred
validation pattern (accept at `n.add()`, catch at `optimize()`) is the primary
weakness -- early validation at component addition time would improve the
debugging experience for interactive network construction. No silent failures
were observed.
