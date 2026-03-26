---
test_id: D-3
tool: pandapower
dimension: accessibility
network: N/A
protocol_version: v11
skill_version: v2
test_hash: 2d316c94
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

# D-3: Example Verification

## Result: INFORMATIONAL

## Finding

14 of 16 tested examples pass without modification. Two failures: (1) the getting-started
example fails due to a zero-length line causing a divide-by-zero error, and (2) the case9
DC OPF fails silently with `converged=False` despite having valid cost functions.

## Evidence

### Method

Ran pandapower's official getting-started examples and built-in example networks inside the
devcontainer (Ubuntu 24.04, Python 3.12, pandapower 3.4.0). All tests executed on 2026-03-24.

### Getting-Started Example (pandapower.org/start/)

The official minimal example creates a 3-bus network with ext_grid, load, transformer,
and line, then runs AC power flow.

**Result: FAIL** — `divide by zero encountered in divide` when creating a zero-length line
(`length_km=0`). This is an error in the example code (should use a nonzero length) or a
missing validation in `create_line()`.

### Built-in Example Networks (AC Power Flow)

| Network | Function | Result |
|---------|----------|--------|
| example_simple | `pn.example_simple()` | PASS |
| example_multivoltage | `pn.example_multivoltage()` | PASS |

### MATPOWER/IEEE Test Cases (AC Power Flow)

| Case | Function | Buses | Result |
|------|----------|-------|--------|
| case4gs | `pn.case4gs()` | 4 | PASS |
| case5 | `pn.case5()` | 5 | PASS |
| case6ww | `pn.case6ww()` | 6 | PASS |
| case9 | `pn.case9()` | 9 | PASS |
| case14 | `pn.case14()` | 14 | PASS |
| case24_ieee_rts | `pn.case24_ieee_rts()` | 24 | PASS |
| case30 | `pn.case30()` | 30 | PASS |
| case39 | `pn.case39()` | 39 | PASS |
| case57 | `pn.case57()` | 57 | PASS |
| case118 | `pn.case118()` | 118 | PASS |
| case300 | `pn.case300()` | 300 | PASS |

### DC Power Flow

| Case | Function | Result |
|------|----------|--------|
| case39 | `pp.rundcpp(net)` | PASS |

### DC OPF

| Case | Function | Result |
|------|----------|--------|
| case9 | `pp.rundcopp(net)` | FAIL (converged=False) |

**case9 DC OPF failure analysis:** The case9 network loaded via `pn.case9()` includes
polynomial cost functions for all three generators. Despite having costs and constraints,
`rundcopp()` reports `converged=False` with no exception or diagnostic message. The PYPOWER
interior-point solver silently fails to converge. This is consistent with the documented
caveat about poor OPF convergence properties, but the silent failure with no diagnostic is
a usability concern.

### Summary

| Category | Count |
|----------|-------|
| Examples run without modification | 14 of 16 |
| Examples needing fixes | 0 |
| Examples that fail | 2 (getting-started zero-length line, case9 DC OPF) |

## Implications

The core example suite is solid — all AC power flow examples work on all test cases from
case4 through case300. The two failures are notable: the getting-started example failure
means a new user's very first interaction may produce an error, and the case9 DC OPF
failure demonstrates the PYPOWER solver's convergence limitations on a standard test case.
Neither failure blocks evaluation, but both reduce first-contact accessibility.
