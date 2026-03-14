---
test_id: A-4
tool: pandapower
dimension: expressiveness
network: TINY
status: pass
workaround_class: null
blocked_by: null
protocol_version: "v10"
skill_version: "v1"
test_hash: "8531c61c"
wall_clock_seconds: 1.88
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 289
solver: null
timestamp: "2026-03-13T00:00:00Z"
---

# A-4: AC feasibility check on DC OPF dispatch

## Result: PASS

## Approach

1. **Solve DC OPF** (same setup as A-3): Load network, apply differentiated costs, derate branches to 70%, solve via `pp.rundcopp(net)`.
2. **Fix generator dispatch:** Set each `net.gen.at[idx, "p_mw"]` to the DC OPF dispatch value. The ext_grid (slack bus) absorbs any real power imbalance from AC losses.
3. **Restore original branch ratings:** Divide `max_i_ka` back by 0.70 to use full thermal limits for the AC feasibility check.
4. **Run ACPF:** `pp.runpp(net, algorithm='nr', init='dc', calculate_voltage_angles=True, tolerance_mva=1e-8, max_iteration=30)`.
5. **Identify violations:** Check voltage magnitudes against [0.95, 1.05] pu band, line/trafo loading against 100%, and generator reactive power against Q limits.

The entire workflow operates on the same `net` object -- no file export/reimport is needed. Generator active power is fixed by setting `p_mw` directly in the gen DataFrame, and the ACPF solver respects these values as PV bus setpoints.

**Unit consistency:** base_power = 100 MVA, dispatch in MW, limits in MW (derived from `max_i_ka` and `vn_kv`). All consistent within the pandapower framework.

## Output

| Metric | Value |
|--------|-------|
| DC OPF converged | True |
| DC OPF total generation | 6254.23 MW |
| ACPF converged | True (DC warm start) |
| ACPF solve time | 0.97 s |
| AC total P losses | 50.20 MW |

**Voltage violations (outside [0.95, 1.05] pu):**

| Bus | Vm (pu) | Violation |
|-----|---------|-----------|
| 21 | 1.0515 | High (+0.15%) |
| 35 | 1.0636 | High (+1.36%) |

**Thermal violations (loading > 100%):** None. Max line loading = 73.5%.

**Transformer violations:** None. Max trafo loading = 83.8%.

**Reactive power violations:** 1 generator exceeds Q limits.

**Generator P deviation (AC vs DC dispatch):** Max = 0.0 MW, Mean = 0.0 MW. pandapower's ACPF respects the fixed `p_mw` values exactly for PV buses.

## Workarounds

None required. pandapower's DataFrame-based data model makes the DC OPF to ACPF workflow straightforward:
1. Solve DC OPF with `rundcopp()`.
2. Read dispatch from `net.res_gen["p_mw"]`.
3. Write dispatch to `net.gen["p_mw"]`.
4. Solve ACPF with `runpp()`.

All within the same model context, no serialization needed.

## Timing

- **Wall-clock:** 1.88 s (DC OPF + AC PF + setup)
- **Timing source:** measured
- **Peak memory:** not measured
- **ACPF solve time:** 0.97 s
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pandapower/tests/expressiveness/test_a4_ac_feasibility_check.py`
