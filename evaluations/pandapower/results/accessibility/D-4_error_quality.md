---
test_id: D-4
tool: pandapower
dimension: accessibility
network: N/A
protocol_version: v11
skill_version: v2
test_hash: 95072651
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
timestamp: "2026-03-24T00:00:00Z"
---

# D-4: Error Quality

## Result: INFORMATIONAL

## Finding

pandapower's error diagnostics are weak for optimization problems (OPF provides only a
boolean `converged` flag with no infeasibility or convergence failure information) but
adequate for element creation (clear warnings for invalid bus references). Topological
issues (disconnected components) are silently ignored.

## Evidence

### Method

Introduced deliberate errors into pandapower networks and assessed diagnostic output quality.
All tests run in devcontainer (pandapower 3.4.0) on 2026-03-24.

### D-4a: Infeasible OPF (line thermal limit set to 0)

**Setup:** `net.line.loc[0, "max_i_ka"] = 0.0` on case9, then `pp.rundcopp(net)`.

**Result:**
```
Converged: False
```

No exception raised. No warning. No error message. The function returns normally with
`net.converged = False`. The solver provides zero diagnostic information about why the
OPF failed. Users cannot distinguish "problem is infeasible" from "solver did not converge."

**Error quality: POOR.** Silent failure with boolean-only status. [tool-specific]

### D-4b: Missing generator cost curve

**Setup:** Cleared all rows from `net.poly_cost` on case9, then `pp.rundcopp(net)`.

**Result:**
```
Converged: False
Stdout message: "no costs are given - overall generated power is minimized"
```

A message printed to stdout (not as a Python warning) indicates the solver falls back to
minimizing total generation. Despite this fallback, convergence still fails.

**Error quality: FAIR.** The fallback is communicated via a print statement, but:
- Not a proper Python warning (cannot be captured by `warnings.filterwarnings`)
- Subsequent convergence failure produces no additional diagnostic
- Users cannot determine if failure is due to missing costs or another issue

### D-4c: Invalid bus reference

**Setup:** `pp.create_load(net, bus=999, p_mw=1.0)` where bus 999 does not exist.

**Result:**
```
UserWarning: Cannot attach to bus 999, 999 does not exist
```

**Error quality: GOOD.** Clear, specific error message identifying the invalid bus number.
Raised as a Python `UserWarning` (catchable). Best error message observed across all tests.

### D-4c (alt): Invalid bus type column

**Setup:** `net.bus.loc[0, "type"] = "invalid_type_xyz"` then `pp.runpp(net)`.

**Result:** Converged successfully. No error or warning. The `type` column is a free-text
metadata field, not a functional bus type selector. PQ/PV/slack is determined by connected
elements, not the type field. This is valid by design.

### D-4d: Disconnected bus with load

**Setup:** Added a new bus (not connected to any branch) with a 100 MW load.

**Result:**
```
Converged: True
NaN bus results: 1
```

Power flow converges successfully, silently ignoring the disconnected bus and its load.
The disconnected bus shows NaN values in `res_bus` but no warning is raised.

**Error quality: POOR.** A disconnected bus carrying 100 MW of load is almost certainly a
modeling error, but pandapower silently ignores it. [tool-specific]

### Error Quality Summary

| Error Type | Diagnostic Quality | Error Message | Actionable? |
|------------|-------------------|---------------|-------------|
| Infeasible OPF | POOR | None (boolean only) | No |
| Missing cost curve | FAIR | Print to stdout | Partially |
| Invalid bus reference | GOOD | Clear UserWarning | Yes |
| Invalid bus type | N/A (by design) | Field is metadata | N/A |
| Disconnected load bus | POOR | None (silent NaN) | No |

## Implications

The OPF diagnostic gap is the most significant finding. The PYPOWER interior-point solver
provides only a binary converged/not-converged signal with no information about infeasibility,
constraint violations, or solver progress. This forces users into trial-and-error debugging
for any OPF convergence issue. Input validation is better for element creation but absent for
topological issues. The AC power flow solver has somewhat better diagnostics through the
optional `Diagnostic` class, but this is a separate post-hoc tool rather than integrated
solver feedback.
