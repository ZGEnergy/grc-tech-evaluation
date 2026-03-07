---
test_id: A-3
tool: pandapower
dimension: expressiveness
network: MEDIUM
protocol_version: "v4"
status: qualified_pass
workaround_class: stable
wall_clock_seconds: 20.66
peak_memory_mb: null
loc: 123
solver: PYPOWER interior point
timestamp: 2026-03-06T00:00:00Z
---

# A-3: Solve DC OPF with gen costs and line flow limits

## Result: QUALIFIED PASS

## Approach

Loaded ACTIVSg10k (~10,000 buses) and solved DC OPF using `pp.rundcopp(net)`. Cost curves imported from MATPOWER case (2,485 polynomial cost entries). Line limits present in the imported data.

## Output

| Metric | Value |
|--------|-------|
| Bus count | 10,000 |
| Generators | 1,727 (+ 1 ext_grid) |
| Converged | Yes |
| Objective | 2,437,763.82 |
| Total generation | 134,323.8 MW |
| LMP range | 20.738 -- 20.738 |
| LMP mean | 20.738 |
| LMPs extractable | Yes |

LMPs are nearly uniform across all buses (~20.738), indicating no binding line constraints in the DC OPF solution.

LMPs extracted from `net.res_bus["lam_p"]`.

## Workarounds

- **What:** Solver deviation -- eval-config specifies HiGHS/GLPK but pandapower's `rundcopp()` uses PYPOWER interior point solver exclusively.
- **Why:** pandapower's DC OPF is hard-wired to PYPOWER's interior point method. No option to swap in HiGHS or GLPK.
- **Durability:** stable -- the PYPOWER solver works and produces correct results; the limitation is solver choice, not correctness.
- **Grade impact:** Minor -- converges and produces LMPs. Solver swap not possible.

## Timing

- **Wall-clock:** 20.66 s
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/pandapower/tests/expressiveness/test_a3_dcopf_medium.py`
