---
test_id: B-9
tool: powersimulations
dimension: extensibility
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: null
peak_memory_mb: null
loc: 10
solver: null
timestamp: "2026-03-07T05:00:00Z"
---

# B-9: PTDF Matrix Extraction

## Result: PASS

## Approach

PTDF matrix extracted using `PowerNetworkMatrices.PTDF(sys)` -- a single function call.
The matrix is computed from the system topology and branch impedances.

```julia
using PowerNetworkMatrices
ptdf = PTDF(sys)
```

## Output

| Metric | Value |
|--------|-------|
| Data dimensions | 39 x 46 (buses x branches) |
| Row axes | Bus numbers (Int64): [1, 2, 3, ...] |
| Column axes | Branch names (String): ["bus-1-bus-2-i_1", ...] |
| Storage type | `PTDF{...}` with `.data::Matrix{Float64}` |
| Computation time | < 1s on TINY |

**Note on dimensions:** PowerNetworkMatrices stores the PTDF as (buses x branches),
which is the transpose of the conventional PTDF convention (branches x buses).
Flows are computed as `ptdf.data' * injections` (transpose times injection vector).

**Indexed access:** `ptdf["bus-1-bus-2-i_1", 1]` returns the sensitivity of branch
"bus-1-bus-2-i_1" to injection at bus 1. The PTDF object supports named lookup
via its custom axes.

### Flow Verification

PTDF-predicted flows match DCPF results to machine precision:

```
ptdf_flows = ptdf.data' * P_injection   # (46,) vector
dcpf_flows = solve_powerflow(DCPowerFlow(), sys)
```

| Branch | PTDF Flow | DCPF Flow |
|--------|-----------|-----------|
| bus-1-bus-2-i_1 | -1.7835 | -1.7835 |
| bus-1-bus-39-i_2 | 0.8075 | 0.8075 |
| bus-2-bus-3-i_3 | 3.3343 | 3.3343 |
| bus-2-bus-25-i_4 | -2.6178 | -2.6178 |
| bus-2-bus-30-i_5 | -2.5000 | -2.5000 |

**Maximum flow error:** 1.15e-14 (machine epsilon level).

The PTDF matrix from PowerNetworkMatrices.jl is the same matrix used internally by
PSI's `PTDFPowerModel` formulation, confirming consistency between the power flow
and optimization solve paths.

### LODF Matrix

LODF (Line Outage Distribution Factor) matrix is also available:

```julia
lodf = LODF(sys)  # 46 x 46 for TINY
```

### Matrix Access Patterns

```julia
ptdf.data              # Raw Matrix{Float64} (39 x 46)
ptdf.axes[1]           # Row labels (bus numbers)
ptdf.axes[2]           # Column labels (branch names)
ptdf["branch_name", bus_num]  # Named element access
```

`Matrix(ptdf)` does NOT work due to custom axis types -- use `ptdf.data` instead.

## Workarounds

None required. `PTDF(sys)` is a one-liner.

## Test Script

Verified via interactive probe in the devcontainer. Also used in DCPF validation
(A-1) and PSI's `PTDFPowerModel` internally.
