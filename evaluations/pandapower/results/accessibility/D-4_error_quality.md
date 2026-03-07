---
test_id: D-4
tool: pandapower
dimension: accessibility
network: TINY
protocol_version: "v4"
status: qualified_pass
workaround_class: null
wall_clock_seconds: null
peak_memory_mb: null
loc: null
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# D-4: Error Quality

## Result: QUALIFIED PASS

## Finding

Of three deliberate errors tested, one produces a meaningful diagnostic (infeasible OPF),
one fails silently with misleading behavior (missing cost curve), and one fails silently
with no error (invalid bus type). Error quality is mixed: OPF infeasibility is caught
clearly, but data validation gaps allow invalid configurations to produce results without
warning.

## Evidence

### (a) Infeasible OPF: line limits set to near-zero

**Input:** Set `net.line["max_i_ka"] = 0.0001` (effectively zero capacity), then run `rundcopp()`.

**Result:** Meaningful diagnostic.

```
Exception type: OPFNotConverged
Exception message: Optimal Power Flow did not converge!
```

The `OPFNotConverged` exception is raised with a clear message. The exception type is specific
to OPF (not a generic solver error). This is the best error behavior of the three tests.

**Assessment:** Good. Clear, specific exception with descriptive message.

### (b) Missing generator cost curve

**Input:** Clear all entries from `net.poly_cost` and `net.pwl_cost` DataFrames, then run
`rundcopp()`.

**Result:** Silent fallback with misleading behavior.

```
OPF_converged: True
(stderr): no costs are given - overall generated power is minimized
```

pandapower prints a warning to stderr ("no costs are given - overall generated power is
minimized") but does NOT raise an exception. The OPF converges with a substitute objective
(minimize total generation). This is problematic because:

1. The warning goes to stderr, not through Python's `warnings` module, so it cannot be
   caught programmatically.
2. `net["OPF_converged"]` is `True`, giving no indication that the cost curves were missing.
3. The substitute objective (minimize generation) may produce a dispatch that appears valid
   but is economically meaningless.
4. A user who does not read stderr carefully would believe their OPF with costs succeeded.

**Assessment:** Poor. Silent fallback to a different objective function. Should raise an
exception or at minimum use `warnings.warn()`.

### (c) Invalid bus type

**Input:** Set `net.bus["type"] = "invalid_type"` for all buses, then run `rundcpp()`.

**Result:** Fails silently.

```
Converged: True
Bus results: 39 rows
```

pandapower accepts the invalid bus type string and produces power flow results without any
error or warning. The `type` column in `net.bus` is a free-form string field (not validated
against an enum). The internal PYPOWER conversion ignores this field for DC power flow.

**Additional test (c2):** Setting a generator's bus reference to a non-existent bus index
(9999) produces:

```
Exception type: IndexError
Exception message: index 9999 is out of bounds for axis 0 with size 39
```

This is a raw numpy IndexError from the internal conversion, not a pandapower-specific
validation error. The message does not identify which element has the invalid bus reference.

**Assessment:** Poor for bus type validation. The tool performs no input validation on bus
type strings. The IndexError for invalid bus references is a raw internal error, not a
user-friendly diagnostic.

## Implications

Error quality is uneven. OPF infeasibility (test a) produces a clean, specific exception --
this is the most likely error a user would encounter and it is handled well. However, missing
cost curves (test b) and invalid bus types (test c) expose gaps in input validation. The
missing-cost fallback is particularly concerning because it silently changes the optimization
objective. For a production-grade tool, these silent failures could lead to incorrect results
without any indication of error. This supports a qualified pass: the most common error case
is handled well, but edge cases reveal insufficient input validation.
