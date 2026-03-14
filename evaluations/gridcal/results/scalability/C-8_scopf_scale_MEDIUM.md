---
test_id: C-8
tool: gridcal
dimension: scalability
network: MEDIUM
status: pass
workaround_class: null
blocked_by: null
protocol_version: "v10"
skill_version: v1
test_hash: "3610913b"
wall_clock_seconds: 29.306
timing_source: measured
peak_memory_mb: 5907.90
convergence_residual: null
convergence_iterations: null
loc: 257
solver: "HiGHS"
timestamp: "2026-03-13T22:40:00Z"
---

# C-8: SCOPF (N-1, 50 contingencies) on MEDIUM

## Result: PASS

## Approach

Scaled C-8 SMALL (SCOPF with 50 contingencies on 2000-bus, 5.45s) to MEDIUM (10000-bus,
12706 branches, 2485 generators). Used the same LODF-based SCOPF formulation via
`consider_contingencies=True` in `OptimalPowerFlowOptions`.

**Contingency selection:** Top 50 most-loaded branches from the base-case DCOPF solution,
sorted by loading percentage descending. The most loaded branch was at 84.72%, the least
loaded in the selected set at 67.06%.

**Steps:**
1. Solved base-case DCOPF for comparison and contingency selection (5.85 s)
2. Created 50 `ContingencyGroup` objects, each with a single `Contingency` deactivating
   one branch
3. Ran SCOPF with `consider_contingencies=True` and `contingency_groups_used=tuple(groups)`

## Output

| Metric | Base DCOPF | SCOPF | Difference |
|--------|-----------|-------|------------|
| Total gen (MW) | 150,916.88 | 150,916.88 | ~0.0 |
| LMP min ($/MWh) | 20.064 | 20.064 | ~0.0 |
| LMP max ($/MWh) | 20.064 | 20.064 | ~0.0 |
| Max loading (%) | 84.72 | 84.72 | 0.0 |
| Binding branches | 0 | 0 | 0 |
| Solve time (s) | 5.85 | 29.31 | -- |

**LMP and dispatch comparison:** The SCOPF produces results nearly identical to the
base-case DCOPF. The maximum dispatch difference is 2.67e-07 MW and the maximum LMP
difference is 1.49e-08 $/MWh -- effectively zero. No generators show dispatch changes
above 1 MW, and no branches become binding.

This is consistent with the ACTIVSg10k network being uncongested (max loading 84.72%).
Since no branches are near their limits in the base case, N-1 contingencies do not create
post-contingency violations that would require redispatch. The SCOPF correctly determines
that the base-case dispatch is already N-1 secure.

**Contrast with SMALL:** On the SMALL (2000-bus) network, SCOPF produced meaningful
redispatch (up to 164 MW shifts) and LMP spread (17.17-19.07 $/MWh) because that network
had branches loaded up to 91.9%. The MEDIUM network's lower loading means the
contingency constraints are non-binding.

### Scale Comparison

| Metric | SMALL | MEDIUM | Ratio |
|--------|-------|--------|-------|
| Bus count | 2,000 | 10,000 | 5.0x |
| Branch count | 3,206 | 12,706 | 3.96x |
| SCOPF time (s) | 5.45 | 29.31 | 5.38x |
| Peak memory (MB) | 374.23 | 5,907.90 | 15.8x |

Time scales roughly linearly with bus count (5.38x for 5x buses). Memory scales
super-linearly (15.8x) due to the LODF matrix and contingency constraint storage
growing quadratically with branch count.

## Workarounds

None required. The `consider_contingencies=True` option, `Contingency`/`ContingencyGroup`
API, and LODF-based security constraints are documented public features that work
identically at SMALL and MEDIUM scale.

## Timing

- **Wall-clock:** 47.77 s (total including base-case comparison)
- **SCOPF solve only:** 29.31 s
- **Base-case DCOPF:** 5.85 s
- **Timing source:** measured
- **Peak memory:** 5,907.90 MB
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/gridcal/tests/scalability/test_c8_scopf_scale_medium.py`
