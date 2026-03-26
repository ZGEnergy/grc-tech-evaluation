---
test_id: A-3
tool: pandapower
dimension: expressiveness
network: TINY
protocol_version: "v11"
skill_version: "v2"
test_hash: "4e20f5bb"
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 4.77
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 305
solver: "PYPOWER interior-point (bundled)"
timestamp: "2026-03-24T00:00:00Z"
---

# A-3: Solve DC OPF with differentiated gen costs and 70% branch derating on TINY (case39)

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
| Max LMP | $88.13/MWh |
| Min LMP | $12.09/MWh |
| **LMP spread** | **$76.05/MWh** |
| Lines above 95% loading | 7 |
| Max line loading | 100.00% |
| Objective value | extracted from `net._ppc["f"]` |
| Solve time | 0.72 s |

**Hard constraint verification:** Max line loading = 1.000000e+02% (= 1.0 p.u. within tolerance). No branch exceeds the derated thermal limit by more than 1e-4 p.u. The PYPOWER interior-point solver enforces branch flow limits as hard constraints.

**Generator dispatch (MW):**

| Element | Bus | Tech | Dispatch (MW) | Pmax (MW) |
|---------|-----|------|---------------|-----------|
| ext_grid 0 | 30 | Hydro | 1342.4 | flexible |
| gen 0 | 29 | Nuclear | 708.6 | 1040 |
| gen 1 | 31 | Nuclear | 556.8 | 646 |
| gen 2 | 32 | Coal | 592.0 | 652 |
| gen 3 | 33 | Coal | 508.0 | 508 |
| gen 4 | 34 | Nuclear | 687.0 | 687 |
| gen 5 | 35 | Gas CC | 203.3 | 580 |
| gen 6 | 36 | Nuclear | 343.4 | 564 |
| gen 7 | 37 | Nuclear | 865.0 | 865 |
| gen 8 | 38 | Gas CC | 447.8 | 1100 |

**LMP extraction:** LMPs are available via the public API: `net.res_bus["lam_p"]` column is populated after `rundcopp()`, containing bus-level Lagrange multipliers on the power balance constraint. No workaround needed.

**Branch shadow prices:** The PYPOWER interior-point solver reports non-zero shadow prices (MU_SF/MU_ST) for all 46 branches, which is characteristic of interior-point methods that approach constraint boundaries asymptotically rather than producing exact zeros. The 7 lines above 95% loading represent the genuinely congested branches. Shadow prices are extracted from `net._ppc["branch"][:, 13:15]`.

**Binding branches:** With 7 lines above 95% loading and the full LMP spread of $76/MWh, the >= 2 binding branch threshold is comfortably exceeded.

## Workarounds

None required. LMPs are accessible via the public `net.res_bus["lam_p"]` column after `rundcopp()`. Branch shadow prices require accessing the internal `net._ppc` structure, but bus-level LMPs via the public API are sufficient for the pass condition.

## Timing

- **Wall-clock:** 4.77 s (includes network loading and cost setup; solve-only: 0.72 s)
- **Timing source:** measured
- **Peak memory:** not measured
- **Solver iterations:** not reported by PYPOWER DC OPF solver
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pandapower/tests/expressiveness/test_a3_dcopf.py`
