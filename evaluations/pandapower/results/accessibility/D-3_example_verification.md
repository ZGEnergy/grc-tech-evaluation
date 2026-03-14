---
test_id: D-3
tool: pandapower
dimension: accessibility
network: N/A
status: informational
workaround_class: null
timestamp: "2026-03-13T18:00:00Z"
protocol_version: "v10"
skill_version: "v1"
test_hash: "2d316c94"
---

# D-3: Example Verification

## Method

Ran pandapower's official getting-started examples and built-in example networks in the
devcontainer. Examples sourced from:
- pandapower.org/start/ (official getting-started page)
- `pandapower.networks` module (built-in example and test networks)

## Results

### Getting-Started Example (pandapower.org/start/)

The official minimal example creates a 3-bus network with ext_grid, load, transformer,
and line, then runs AC power flow.

| Step | Result |
|------|--------|
| Create empty network | PASS |
| Create buses (20kV, 0.4kV) | PASS |
| Create ext_grid, load | PASS |
| Create transformer, line (std_types) | PASS |
| `pp.runpp(net)` | PASS (converged) |
| Access `net.res_bus`, `net.res_line` | PASS |

**Verdict: PASS** — Example runs without modification.

### Built-in Example Networks

| Network | Function | Converged | Buses | Verdict |
|---------|----------|-----------|-------|---------|
| Simple example | `pn.example_simple()` | Yes | 7 | PASS |
| Multivoltage example | `pn.example_multivoltage()` | Yes | 57 | PASS |

### MATPOWER/IEEE Test Cases (AC Power Flow)

| Case | Function | Converged | Buses | Verdict |
|------|----------|-----------|-------|---------|
| case4gs | `pn.case4gs()` | Yes | 4 | PASS |
| case5 | `pn.case5()` | Yes | 5 | PASS |
| case6ww | `pn.case6ww()` | Yes | 6 | PASS |
| case9 | `pn.case9()` | Yes | 9 | PASS |
| case14 | `pn.case14()` | Yes | 14 | PASS |
| case24_ieee_rts | `pn.case24_ieee_rts()` | Yes | 24 | PASS |
| case30 | `pn.case30()` | Yes | 30 | PASS |
| case39 | `pn.case39()` | Yes | 39 | PASS |
| case57 | `pn.case57()` | Yes | 57 | PASS |
| case118 | `pn.case118()` | Yes | 118 | PASS |
| case300 | `pn.case300()` | Yes | 300 | PASS |

### DC Power Flow

| Case | Function | Converged | Verdict |
|------|----------|-----------|---------|
| case39 | `pp.rundcpp(net)` | Yes | PASS |

### DC OPF

| Case | Function | Converged | Verdict |
|------|----------|-----------|---------|
| case9 | `pp.rundcopp(net)` | No | FAIL |

**case9 DC OPF failure analysis:** The case9 network as loaded by `pn.case9()` includes
polynomial cost functions for all three generators. Despite having costs and constraints,
`rundcopp()` reports `converged=False` with no exception or diagnostic message. The
PYPOWER interior-point solver silently fails to converge. This is consistent with the
documented caveat: "The optimization with pypower functionality does not have the best
convergence properties."

This is a notable finding: a built-in test case with built-in cost functions fails to
solve its own OPF out of the box, with no diagnostic output to help the user understand
why.

## Summary

| Category | Count |
|----------|-------|
| Examples run without modification | 15 of 16 |
| Examples needing fixes | 0 |
| Examples that fail | 1 (case9 DC OPF) |

The getting-started example and all AC power flow examples work perfectly. The single
failure is the PYPOWER-based DC OPF on case9, which fails silently without diagnostics.
