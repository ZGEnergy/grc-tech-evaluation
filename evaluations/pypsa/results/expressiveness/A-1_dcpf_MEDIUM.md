---
test_id: A-1
tool: pypsa
dimension: expressiveness
network: MEDIUM
protocol_version: v9
skill_version: v1
test_hash: 32fb2553
status: pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 21.99
timing_source: measured
peak_memory_mb: 2099.0
convergence_residual: null
convergence_iterations: null
loc: 169
solver: null
timestamp: 2026-03-11T00:00:00Z
---

# A-1: DC Power Flow (dcpf) — MEDIUM

## Result: PASS

## Approach

Same pipeline as TINY: `matpowercaseframes.CaseFrames` → PYPOWER ppc dict → `n.import_from_pypower_ppc(ppc, overwrite_zero_s_nom=True)` → `n.lpf()`. The `overwrite_zero_s_nom=True` parameter replaces the 2462 zero-rated lines in ACTIVSg10k with 1.0 MVA capacity (for DCPF this has no effect since DCPF does not enforce flow limits — it only affects the s_nom attribute).

Peak memory and wall-clock timing tracked via `tracemalloc` and `time.perf_counter()`.

## Output

**Network:** 10,000 buses, 9,726 lines, 2,980 transformers, 2,485 generators, 4,170 loads

**Convergence:** Solved (linear system — guaranteed convergence)

**Voltage Angles (degrees, first 5 buses):**

| Bus | Angle (deg) |
|-----|-------------|
| 10001 | 48.681 |
| 10002 | 51.534 |
| 10003 | 54.656 |
| 10004 | 54.777 |
| 10005 | 54.770 |

**Line Flows p0 (MW, first 5 lines):**

| Line | Flow (MW) |
|------|-----------|
| L0 | 16.72 |
| L1 | -7.08 |
| L2 | 32.70 |
| L3 | 2.88 |
| L4 | 19.41 |

**Summary statistics:**
- Non-zero voltage angles: 9,999 of 10,000 buses (1 slack bus at 0)
- Non-zero line flows: 9,532 of 9,726 lines
- Max voltage angle: 104.88 degrees
- Max line flow: 1,839.6 MW
- Total load: 150,917 MW
- Slack bus: 40845

**Note:** Max angle of 104.88° is high but not unusual for a 150 GW continental-scale synthetic network. The DCPF linear model does not enforce angle limits.

## Workarounds

- **What:** Used `matpowercaseframes.CaseFrames` to parse `.m` file, manually constructed PYPOWER ppc dict, then called `n.import_from_pypower_ppc(ppc, overwrite_zero_s_nom=True)`.
- **Why:** PyPSA has no native MATPOWER .m reader.
- **Durability:** stable — same as TINY, documented companion package usage.
- **Grade impact:** Same as TINY (B-level, standard pipeline).

## Timing

- **Wall-clock:** 21.99 s (total including load + solve + extraction)
- **Load time:** 1.39 s
- **Solve time (lpf only):** 20.56 s
- **Timing source:** measured
- **Peak memory:** 2,099 MB (2.05 GB)
- **CPU cores used:** 1

**Scale comparison vs TINY:**
- TINY (39 buses): lpf solve = 0.065 s
- MEDIUM (10,000 buses): lpf solve = 20.6 s (~317× slower, ~256× more buses)
- Roughly O(n²) scaling, consistent with sparse linear algebra on dense sub-network matrix

## Test Script

**Path:** `evaluations/pypsa/tests/expressiveness/test_a1_dcpf_medium.py`
