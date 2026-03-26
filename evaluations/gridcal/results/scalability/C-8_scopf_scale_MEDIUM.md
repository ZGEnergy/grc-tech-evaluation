---
test_id: C-8
tool: gridcal
dimension: scalability
network: MEDIUM
protocol_version: "v11"
skill_version: v2
test_hash: "e73dfb3f"
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 32.123
timing_source: measured
peak_memory_mb: 5907.90
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 300
solver: "HiGHS"
cpu_threads_used: 1
cpu_threads_available: 32
timestamp: 2026-03-24T18:00:00Z
---

# C-8: SCOPF (N-1, 50 contingencies) on MEDIUM (load-scaled congested version)

## Result: PASS

## Approach

SCOPF on the ACTIVSg 10000-bus network with 50 N-1 contingencies. Per v11 protocol,
branch ratings were derated to 80% of original values to create congestion (the base
ACTIVSg10k network is uncongested at ~84% max loading). This derating produces binding
branch constraints and enables the SCOPF to demonstrate meaningful security-constrained
redispatch.

**Congestion creation:** Branch ratings multiplied by 0.80 (derated to 80%). After
derating, the base-case DCOPF shows 2 branches exceeding 100% loading and an LMP spread
of 144.91 $/MWh, confirming congestion is present.

**Note on soft constraints:** The base-case DCOPF with derated branches shows max loading
of 101.87% -- branches slightly exceed their limits due to GridCal's soft-constraint
formulation (LP slack variables). This is a documented tool characteristic from A-3,
not a SCOPF issue. [tool-specific: soft branch constraints allow slight overloading]

**Steps:**
1. Loaded network and derated branch ratings to 80%
2. Solved base-case DCOPF for comparison and contingency selection (4.97 s)
3. Selected top 50 most-loaded branches as contingencies (101.87% to 83.46%)
4. Created 50 `ContingencyGroup` objects, each with a single `Contingency` deactivating
   one branch
5. Ran SCOPF with `consider_contingencies=True` and `contingency_groups_used=tuple(groups)`

## Output

| Metric | Base DCOPF | SCOPF | Difference |
|--------|-----------|-------|------------|
| Total gen (MW) | 150,916.88 | 150,916.88 | ~0.0 |
| LMP min ($/MWh) | -82.63 | -83.67 | -1.05 |
| LMP max ($/MWh) | 62.29 | 63.35 | +1.07 |
| LMP spread ($/MWh) | 144.91 | 147.03 | +2.11 |
| Max loading (%) | 101.87 | 102.13 | +0.26 |
| Binding branches | 2 | 2 | 0 |
| Aggregate dispatch change | -- | -- | 956.5 MW |
| Solve time (s) | 4.97 | 32.12 | -- |

**Redispatch analysis (v11 5 MW threshold):** The SCOPF produces 956.5 MW aggregate
dispatch change vs the base DCOPF, far exceeding the 5 MW minimum required by the v11
pass condition. This confirms security constraints are active and producing meaningful
redispatch.

**Top generators by dispatch change:**

| Generator | Base MW | SCOPF MW | Diff MW |
|-----------|---------|----------|---------|
| gen_108 | 312.19 | 670.16 | +357.97 |
| gen_1816 | 221.00 | 31.53 | -189.47 |
| gen_1791 | 215.37 | 56.27 | -159.10 |
| gen_1803 | 206.33 | 86.74 | -119.59 |
| gen_1135 | 113.44 | 210.00 | +96.56 |

8 generators show dispatch changes greater than 1 MW. The SCOPF correctly redispatches
generation to maintain N-1 security with derated branch limits.

**LMP spread:** The SCOPF increases LMP spread from 144.91 to 147.03 $/MWh (+2.11),
reflecting the cost of maintaining N-1 security. Maximum LMP difference between base
and SCOPF is 2.86 $/MWh.

### Scale Comparison

| Metric | SMALL | MEDIUM | Ratio |
|--------|-------|--------|-------|
| Bus count | 2,000 | 10,000 | 5.0x |
| Branch count | 3,206 | 12,706 | 3.96x |
| SCOPF time (s) | 5.45 | 32.12 | 5.89x |
| Peak memory (MB) | 374.23 | 5,907.90 | 15.8x |

Time scales roughly linearly with bus count (5.89x for 5x buses). Memory scales
super-linearly (15.8x) due to the LODF matrix and contingency constraint storage
growing quadratically with branch count.

## Workarounds

None required. The `consider_contingencies=True` option, `Contingency`/`ContingencyGroup`
API, and LODF-based security constraints are documented public features that work
identically at SMALL and MEDIUM scale. Branch derating is a standard preprocessing step
applied uniformly to create congestion per the v11 protocol.

## Timing

- **Wall-clock:** 32.12 s (SCOPF solve only)
- **Base-case DCOPF:** 4.97 s
- **Total script time:** 48.76 s (includes base-case + SCOPF)
- **Timing source:** measured
- **Peak memory:** 5,907.90 MB
- **CPU threads used:** 1
- **CPU threads available:** 32

## Test Script

**Path:** `evaluations/gridcal/tests/scalability/test_c8_scopf_scale_medium.py`

Key code showing SCOPF with branch derating:

```python
# Derate branch ratings to create congestion
for br in branches:
    if hasattr(br, "rate") and br.rate > 0:
        br.rate = br.rate * 0.80

# SCOPF with 50 contingencies
opf_opts = vge.OptimalPowerFlowOptions(
    solver=SolverType.LINEAR_OPF,
    mip_solver=MIPSolvers.HIGHS,
    consider_contingencies=True,
    contingency_groups_used=tuple(contingency_groups),
)
results = vge.linear_opf(grid, opf_opts)
```
