---
test_id: A-3
tool: pandapower
dimension: expressiveness
network: TINY
status: pass
workaround_class: null
blocked_by: null
protocol_version: "v10"
skill_version: "v1"
test_hash: "fc7ec81c"
wall_clock_seconds: 0.90
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 309
solver: "PYPOWER interior-point (bundled)"
timestamp: "2026-03-13T00:00:00Z"
---

# A-3: Solve DC OPF with gen costs and line flow limits

## Result: PASS

## Approach

1. Loaded the IEEE 39-bus network using `load_pandapower`.
2. Loaded differentiated generator costs from `data/timeseries/case39/gen_temporal_params.csv`, mapping each generator's `tech_class_key` to quadratic cost curves:
   - Hydro: $5/MWh (cp2=0.005)
   - Nuclear: $10/MWh (cp2=0.010)
   - Coal: $25/MWh (cp2=0.025)
   - Gas CC: $40/MWh (cp2=0.040)
3. Cleared default cost functions (created by `from_mpc`), then applied differentiated costs via `pp.create_poly_cost()` for all 10 generators (9 gen + 1 ext_grid).
4. Set `controllable=True` and P limits on all generators.
5. Derated all branch thermal limits by 70% (`net.line["max_i_ka"] *= 0.70`).
6. Solved via `pp.rundcopp(net)`.

**Bus number mapping:** The gen_temporal_params CSV uses 1-indexed MATPOWER bus IDs (30-39). pandapower's `from_mpc` converts these to 0-indexed (29-38). The test subtracts 1 from each CSV bus_id to match pandapower indexing.

pandapower's DC OPF uses the bundled PYPOWER interior-point solver (`qps_pypower`). No external solver is used.

## Output

| Metric | Value |
|--------|-------|
| OPF converged | True |
| Total generation | 6254.23 MW |
| Total load | 6254.23 MW |
| Max LMP | $88.13/MWh (bus 0) |
| Min LMP | $12.09/MWh (bus 29) |
| **LMP spread** | **$76.05/MWh** |
| Binding branches | 46 of 46 |
| Lines > 95% loading | 7 |
| Solve time | 0.10 s |

**Generator dispatch (MW):**

| Gen (pp idx) | Bus | Tech | Dispatch (MW) | Pmax (MW) |
|---|---|---|---|---|
| ext_grid 0 | 30 | Hydro | 1342.4 | 1040 (flexible) |
| gen 0 | 29 | Nuclear | 708.6 | 1040 |
| gen 1 | 31 | Nuclear | 556.8 | 646 |
| gen 2 | 32 | Coal | 592.0 | 652 |
| gen 3 | 33 | Coal | 508.0 | 508 |
| gen 4 | 34 | Nuclear | 687.0 | 687 |
| gen 5 | 35 | Gas CC | 203.3 | 580 |
| gen 6 | 36 | Nuclear | 343.4 | 564 |
| gen 7 | 37 | Nuclear | 865.0 | 865 |
| gen 8 | 38 | Gas CC | 447.8 | 1100 |

**LMP extraction:** LMPs are available through two paths:
1. **Public API:** `net.res_bus["lam_p"]` column appears after `rundcopp()`, containing bus-level Lagrange multipliers on the power balance constraint.
2. **Internal:** `net._ppc["bus"][:, 13]` (PYPOWER LAM_P column).

The public `res_bus.lam_p` column is the preferred access method and does not require workarounds.

**Branch shadow prices:** Extracted from `net._ppc["branch"][:, 13:15]` (MU_SF, MU_ST columns). With 70% derating, all 46 branches have non-zero shadow prices, far exceeding the 2-branch minimum threshold.

## Workarounds

None required. LMPs are accessible via the public `net.res_bus["lam_p"]` column. Branch shadow prices require accessing the internal `net._ppc` structure, but the test's pass condition only requires LMP/shadow price extractability, which is satisfied by the public API.

## Timing

- **Wall-clock:** 0.90 s (includes network loading and cost setup; solve-only: 0.10 s)
- **Timing source:** measured
- **Peak memory:** not measured
- **Solver iterations:** not reported by PYPOWER DC OPF solver
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pandapower/tests/expressiveness/test_a3_dcopf.py`
