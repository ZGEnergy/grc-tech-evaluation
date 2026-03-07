---
test_id: A-6
tool: pypsa
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: pass
workaround_class: stable
wall_clock_seconds: 3.06
peak_memory_mb: null
loc: 315
solver: highs
timestamp: 2026-03-06T00:00:00Z
---

# A-6: SCED (Security-Constrained Economic Dispatch)

## Result: PASS

## Approach

Implemented a two-stage SCUC-to-SCED workflow on the IEEE 39-bus network (case39):

**Stage 1 -- SCUC (MILP):** Reused the A-5 network setup (24-hour snapshots, 10 generators with `committable=True`, min up/down times, ramp limits, startup/shutdown costs). Solved as MILP via `n.optimize(solver_name="highs")`.

**Stage 2 -- SCED (LP):** Fixed the commitment schedule from Stage 1 and re-solved economic dispatch as a pure LP:

1. Set `committable=False` on all generators (removes binary status variables).
2. Encoded the SCUC commitment into time-varying `p_max_pu` and `p_min_pu` series: when a generator is committed (status=1), bounds remain at normal values (p_max_pu=1.0, p_min_pu=0.3); when decommitted (status=0), both are set to 0.0 to force zero output.
3. Left `ramp_limit_up` and `ramp_limit_down` at 0.3 (30% of p_nom per hour).
4. Solved via `n.optimize()` -- HiGHS confirmed LP (no integer variables), 1344 primals, 4276 duals.

PyPSA does **not** have a dedicated method to fix commitment and re-dispatch (e.g., no `fix_commitment()` or `solve_ed()` shortcut). The `fix_optimal_dispatch()` method exists but fixes all dispatch values, not just commitment -- it is not suitable for the SCUC-to-SCED pattern. The user must manually transfer the commitment schedule by manipulating generator bounds.

### Solver settings

```
solver: highs
time_limit: 300
presolve: on
threads: 1
output_flag: true
```

MILP stage additionally: `mip_rel_gap: 0.01`

## Output

### Stage 1: SCUC

| Metric | Value |
|--------|-------|
| Solver status | Optimal |
| Objective (total cost) | $36,474.67 |
| MIP gap | 0% |
| All 10 generators committed all 24 hours | Yes |

### Stage 2: SCED

| Metric | Value |
|--------|-------|
| Solver status | Optimal |
| Problem type | LP (confirmed: no binary variables) |
| Objective (total cost) | $36,474.67 |
| LP iterations | 672 |
| Solve time (HiGHS) | 0.01s |

### Ramp Constraint Enforcement

Zero ramp violations detected across all generators and all consecutive hours. Ramp constraints are **demonstrably binding** in the ED stage:

| Generator | p_nom (MW) | Ramp Limit (MW) | Max Ramp Up (MW) | Max Ramp Down (MW) | Binding? |
|-----------|-----------|-----------------|------------------|--------------------|---------|
| G0 | 1,040 | 312.0 | 312.0 | 213.7 | Up |
| G2 | 725 | 217.5 | 217.5 | 217.5 | Both |
| G3 | 652 | 195.6 | 195.6 | 195.6 | Both |
| G4 | 508 | 152.4 | 152.4 | 152.4 | Both |
| G5 | 687 | 206.1 | 206.1 | 206.1 | Both |
| G6 | 580 | 174.0 | 174.0 | 174.0 | Both |
| G7 | 564 | 169.2 | 169.2 | 169.2 | Both |
| G8 | 865 | 259.5 | 259.5 | 259.5 | Both |
| G9 | 1,100 | 330.0 | 330.0 | 330.0 | Both |

8 of 10 generators hit their ramp limits at the tightest points of the load profile. G1 (646 MW, slack-like) did not ramp at all. This confirms ramp constraints are actively enforced in the ED LP -- not just inherited from the UC formulation.

### Dispatch Comparison (SCUC vs SCED)

| Metric | Value |
|--------|-------|
| Max dispatch difference | 770 MW |
| Mean dispatch difference | 272 MW |

The SCED re-optimizes dispatch within the fixed commitment envelope. With identical objectives ($36,474.67), both solutions are equally optimal but the LP finds different generator-level allocations. This is expected when multiple dispatch schedules achieve the same cost.

### Two-Stage Separation

The SCUC and SCED stages are **cleanly separable**: the commitment from Stage 1 is encoded into bounds for Stage 2, and Stage 2 solves as a pure LP. The workflow requires ~10 lines of glue code to transfer the commitment schedule.

## Workarounds

- **What:** Fixed commitment by setting `committable=False` and encoding UC status into time-varying `p_min_pu`/`p_max_pu` (0 when decommitted, normal bounds when committed)
- **Why:** PyPSA has no dedicated method for fixing commitment from a prior SCUC solve. `fix_optimal_dispatch()` fixes all dispatch values (not just commitment), and `fix_optimal_capacities()` is for investment planning -- neither supports the SCUC-to-SCED pattern.
- **Durability:** stable -- uses documented public API attributes (`committable`, `p_min_pu`, `p_max_pu`, `generators_t` DataFrames). The pattern of encoding binary decisions into continuous bounds is well-established in power systems.
- **Grade impact:** Minor friction. The workaround is straightforward (~10 LOC) and uses only public API. A dedicated `fix_commitment()` method would be more ergonomic but is not essential.

- **What:** Manually set `marginal_cost` from parsed gencost data
- **Why:** PPC importer does not import gencost columns
- **Durability:** stable -- inherited from A-5, documented public API
- **Grade impact:** Negligible (import friction, not dispatch/commitment related)

## Timing

- **Wall-clock (total):** 3.06s (includes both SCUC and SCED stages + model construction)
- **SCUC solve:** 0.06s (HiGHS MILP)
- **SCED solve:** 0.01s (HiGHS LP)
- **SCED model construction + overhead:** ~0.42s
- **Peak memory:** not measured
- **LP iterations (SCED):** 672
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/expressiveness/test_a6_sced.py`
