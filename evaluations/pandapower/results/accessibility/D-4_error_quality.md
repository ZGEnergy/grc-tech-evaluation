---
test_id: D-4
tool: pandapower
dimension: accessibility
network: N/A
status: informational
workaround_class: null
timestamp: "2026-03-13T18:00:00Z"
protocol_version: "v10"
skill_version: "v1"
test_hash: "95072651"
---

# D-4: Error Quality

## Method

Introduced three categories of deliberate errors into pandapower networks and assessed
the quality of diagnostic output: (a) infeasible OPF, (b) missing generator cost curve,
(c) invalid bus type. All tests run in devcontainer.

## Test Results

### D-4a: Infeasible OPF (line limit set to 0)

**Setup:** `net.line.loc[0, "max_i_ka"] = 0.0` on case9, then `pp.rundcopp(net)`.

**Result:**
```
Converged: False
```

No exception raised. No warning. No error message. The function returns normally with
`net.converged = False`.

**Error quality: POOR.** The solver provides zero diagnostic information about why the
OPF failed. Users must guess whether the problem is infeasible, the solver failed to
converge, or a parameter is invalid. There is no distinction between "problem is
infeasible" and "solver did not converge." The `_ppc` internal dict is populated but
contains no infeasibility information accessible to users.

**Classification: Silent failure with boolean-only status.**

### D-4b: Missing generator cost curve

**Setup:** Cleared all rows from `net.poly_cost` on case9, then `pp.rundcopp(net)`.

**Result:**
```
Converged: False
```

A log message "no costs are given - overall generated power is minimized" is printed to
stdout (not as a Python warning), indicating the solver falls back to minimizing total
generation. Despite this fallback, the solver still reports non-convergence.

**Error quality: FAIR.** The fallback behavior is communicated via a print statement, but:
- It is not a proper Python warning (cannot be captured by `warnings.filterwarnings`)
- The subsequent convergence failure produces no additional diagnostic
- Users cannot tell whether the failure is due to the missing costs or another issue

**Classification: Partial diagnostic via print statement, but no actionable error.**

### D-4c: Invalid bus type

**Setup:** Set `net.bus.loc[0, "type"] = "invalid_type_xyz"` on case9, then `pp.runpp(net)`.

**Result:**
```
Converged: True
```

No error, no warning. The power flow converges normally. The `type` column in `net.bus`
is a free-text metadata field with no validation — it does not affect the power flow
calculation.

**Error quality: N/A (by design).** pandapower's bus `type` column is a user annotation
field, not a functional bus type selector. The functional bus type (PQ/PV/slack) is
determined by what elements are connected to the bus (ext_grid = slack, gen = PV,
load-only = PQ). This is a valid design choice but differs from tools where bus type
is an explicit field.

### D-4c (alt): Invalid bus reference

**Setup:** `pp.create_load(net, bus=999, p_mw=1.0)` where bus 999 does not exist.

**Result:**
```
UserWarning: Cannot attach to bus 999, 999 does not exist
```

**Error quality: GOOD.** Clear, specific error message identifying the invalid bus
number. Raised as a Python `UserWarning` (catchable). This is the best error message
observed across all tests.

### D-4 (additional): Disconnected bus with load

**Setup:** Added a new bus (not connected to any branch) with a 100 MW load, then
`pp.runpp(net)`.

**Result:**
```
Converged: True
```

The power flow converges successfully, silently ignoring the disconnected bus and its
load. The disconnected bus shows NaN values in `res_bus` but no warning is raised.

**Error quality: POOR.** A disconnected bus carrying 100 MW of load is almost certainly
a modeling error, but pandapower silently ignores it. A warning would be appropriate.

## Error Quality Summary

| Error Type | Diagnostic Quality | Error Message | Actionable? |
|------------|-------------------|---------------|-------------|
| Infeasible OPF | POOR | None (boolean only) | No |
| Missing cost curve | FAIR | Print to stdout (not warning) | Partially |
| Invalid bus type | N/A | Field is metadata, not functional | N/A |
| Invalid bus reference | GOOD | Clear UserWarning with bus ID | Yes |
| Disconnected load bus | POOR | None (silent NaN) | No |

## Overall Assessment

pandapower's error diagnostics are weak for optimization problems. The OPF solver
(`rundcopp`, `runopp`) provides only a boolean `converged` flag with no information
about infeasibility, constraint violations, or solver progress. This is inherited from
the PYPOWER interior-point solver which does not distinguish convergence failure modes.

Input validation is better for element creation (bus reference checking) but absent for
topological issues (disconnected components). The AC power flow solver (`runpp`) has
somewhat better diagnostics through the optional `Diagnostic` class, but this is a
separate post-hoc tool rather than integrated into the solver.
