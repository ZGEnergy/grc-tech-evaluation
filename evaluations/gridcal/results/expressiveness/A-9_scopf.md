---
test_id: A-9
tool: gridcal
dimension: expressiveness
network: TINY
status: pass
workaround_class: null
blocked_by: null
protocol_version: "v10"
skill_version: v1
test_hash: "e3ccffc8"
wall_clock_seconds: 1.84
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 242
solver: "HiGHS"
timestamp: "2026-03-13T00:00:00Z"
---

# A-9: DC OPF with N-1 contingency constraints embedded in optimization on TINY

## Result: PASS

## Approach

GridCal supports SCOPF via the `consider_contingencies=True` option in
`OptimalPowerFlowOptions`. The formulation uses LODF-based security constraints added to the
linear OPF within the optimization (not checked post-hoc). Contingencies are defined using
`Contingency` and `ContingencyGroup` objects registered on the grid.

**Setup:**
1. Applied differentiated costs and 70% branch derating (same as A-3).
2. Created 46 N-1 contingencies -- one `ContingencyGroup` per branch, each containing a
   single `Contingency` that deactivates that branch.
3. Registered all contingency groups via `grid.add_contingency_group()` and
   `grid.add_contingency()`.
4. Ran SCOPF with `consider_contingencies=True` and `contingency_groups_used=tuple(groups)`.

**Comparison:** Also ran the base-case DCOPF (without contingencies) using the same network
setup for direct comparison.

## Output

| Metric | Base DCOPF | SCOPF | Difference |
|--------|-----------|-------|------------|
| Total gen (MW) | 6,254.2 | 6,254.2 | 0.0 |
| LMP min ($/MWh) | 5.00 | 5.00 | 0.00 |
| LMP max ($/MWh) | 84.38 | 90.26 | +5.88 |
| Max LMP diff | -- | -- | 7.11 |
| Binding branches | 7 | 6 | -1 |
| SCOPF solve time | -- | 0.067 s | -- |

**Dispatch changes** (generators with >1 MW difference):

| Generator | Base MW | SCOPF MW | Diff MW |
|-----------|---------|----------|---------|
| G0 (Hydro) | 372.4 | 245.3 | -127.0 |
| G7 (Gas CC) | 564.0 | 551.2 | -12.8 |
| G9 (Gas CC) | 891.9 | 1,031.7 | +139.9 |

The SCOPF redispatches generation away from G0 (bus 30) and toward G9 (bus 31) to ensure
N-1 security. This reflects the LODF-based constraint enforcement: removing certain branches
would cause overloads under the base-case dispatch, so the SCOPF pre-positions generation to
avoid post-contingency violations.

**SCOPF binding branches:** 2_3_1, 16_19_1, 10_32_1, 19_33_1, 22_35_1, 29_38_1 (6 branches
at 100% loading). The base-case 6_11_1 branch is no longer binding in the SCOPF solution,
while branch 2_3_1 is now at exactly 100% (vs 112% overloaded in base case).

## Workarounds

None required. The `consider_contingencies` option and `Contingency`/`ContingencyGroup` API
are documented public features. The SCOPF formulation embeds contingency constraints within
the optimization via LODF-based reformulation.

## Timing

- **Wall-clock:** 1.84 s (total including base-case comparison)
- **SCOPF solve only:** 0.067 s
- **Timing source:** measured
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/gridcal/tests/expressiveness/test_a9_scopf.py`

Key code showing SCOPF setup:

```python
# Create N-1 contingencies (one group per branch)
for br in branches:
    cg = ContingencyGroup(name=f"N-1_{br.name}")
    grid.add_contingency_group(cg)
    c = Contingency(
        device=br,
        name=f"ctg_{br.name}",
        prop=ContingencyOperationTypes.Active,
        value=0.0,
        group=cg,
    )
    grid.add_contingency(c)
    contingency_groups.append(cg)

# Run SCOPF
opf_opts = vge.OptimalPowerFlowOptions(
    solver=SolverType.LINEAR_OPF,
    mip_solver=MIPSolvers.HIGHS,
    consider_contingencies=True,
    contingency_groups_used=tuple(contingency_groups),
)
results = vge.linear_opf(grid, opf_opts)
```
