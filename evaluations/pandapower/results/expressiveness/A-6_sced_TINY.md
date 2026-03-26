---
test_id: A-6
tool: pandapower
dimension: expressiveness
network: TINY
protocol_version: "v11"
skill_version: "v2"
test_hash: "aa42ad46"
status: partial_pass
workaround_class: fragile
blocked_by: A-5
wall_clock_seconds: 3.13
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 339
solver: "PYPOWER interior-point (bundled)"
sced_mode: ed_only
timestamp: "2026-03-24T00:00:00Z"
---

# A-6: Fix commitment from A-5, solve economic dispatch

## Result: PARTIAL PASS

**SCED mode:** `ed_only`
**Blocked by:** A-5 (SCUC -- unsupported)

## Approach

Since A-5 (SCUC) failed, A-6 cannot achieve `full_sced`. This test instead demonstrates `ed_only` mode: sequential single-period DC OPF with manual ramp constraint enforcement.

1. Loaded the IEEE 39-bus network using `load_pandapower`.
2. Applied differentiated generator costs from Modified Tiny data (`gen_temporal_params.csv`).
3. Applied 70% branch derating.
4. For each of 24 hours:
   - Scaled bus loads to match the hourly load profile from `load_24h.csv`.
   - Applied ramp constraints by adjusting generator Pmin/Pmax based on previous hour's dispatch and ramp rates from `gen_temporal_params.csv`.
   - Solved single-period DC OPF via `pp.rundcopp(net)`.
   - Extracted dispatch and cost.
5. Verified ramp constraint enforcement post-hoc.

**Commitment assumption:** All generators committed for all 24 hours (no UC from A-5).

## Output

| Metric | Value |
|--------|-------|
| Hours solved | 24 / 24 |
| Total cost (24h, linear) | 2.652054e+06 |
| Solve time (24 OPF calls) | 1.108060e+00 s |
| Ramp binding instances | 0 |
| Ramp violations | 0 |

**Generator dispatch ranges (MW over 24 hours):**

| Generator | Bus | Min MW | Max MW | Range MW |
|-----------|-----|--------|--------|----------|
| gen_0 (Nuclear) | 29 | 705.45 | 757.85 | 52.40 |
| gen_1 (Nuclear) | 31 | 535.70 | 620.66 | 84.96 |
| gen_2 (Coal) | 32 | 150.46 | 592.00 | 441.54 |
| gen_3 (Coal) | 33 | 150.46 | 508.00 | 357.54 |
| gen_4 (Nuclear) | 34 | 687.00 | 687.00 | 0.00 |
| gen_5 (Gas CC) | 35 | 0.00 | 203.30 | 203.30 |
| gen_6 (Nuclear) | 36 | 237.32 | 343.39 | 106.07 |
| gen_7 (Nuclear) | 37 | 644.43 | 865.00 | 220.57 |
| gen_8 (Gas CC) | 38 | 52.75 | 447.76 | 395.01 |
| ext_grid_0 (Hydro) | 30 | 936.27 | 1348.90 | 412.63 |

**Ramp binding:** No ramp constraints were binding (0 instances). This is expected because the Modified Tiny ramp rates are very large relative to hourly load changes (e.g., hydro 62,400 MW/hr, nuclear 1,938 MW/hr), so the OPF solution naturally satisfies ramp limits without being constrained.

**Dispatch extraction:** Generator dispatch is cleanly extractable via `net.res_gen["p_mw"]` and `net.res_ext_grid["p_mw"]` after each `rundcopp()` call.

## Workarounds

- **What:** Manual ramp enforcement via Pmin/Pmax adjustment between sequential single-period DC OPF calls
- **Why:** pandapower has no native multi-period dispatch. Each `rundcopp()` is independent with no temporal coupling. Ramp constraints must be injected by modifying generator bounds between solves.
- **Durability:** fragile -- relies on manipulating generator bounds between sequential single-period solves. The approach is not a documented pattern and produces a greedy (not globally optimal) solution since each hour is optimized independently without look-ahead.
- **Grade impact:** ed_only mode with fragile workaround. No commitment schedule from A-5, no temporal coupling in optimization. This is a meaningful limitation for the expressiveness criterion.

## Timing

- **Wall-clock:** 3.13 s (includes network loading, cost setup, 24 OPF solves)
- **Timing source:** measured
- **Solve-only time:** 1.11 s (24 sequential DC OPF calls)
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/pandapower/tests/expressiveness/test_a6_sced.py`
