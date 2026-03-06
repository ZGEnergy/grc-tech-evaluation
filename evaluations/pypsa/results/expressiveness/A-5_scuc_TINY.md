# A-5: 24-Hour SCUC as MILP (TINY)

- **Test ID:** A-5
- **Slug:** scuc
- **Tool:** PyPSA 1.1.2
- **Network:** IEEE 39-bus (case39.m)
- **Solver:** HiGHS 1.13.1
- **Status:** PASS

## Pass Condition

Solves to feasibility (MIP gap <= 1%). Commitment schedule extractable as time-indexed binary matrix. Built-in constraint types vs user-assembled noted.

## Results

| Metric | Value |
|--------|-------|
| Wall clock | 1.464 s |
| Solver status | optimal |
| MIP gap | 0.097% (well within 1% target) |
| Objective value | 118501.49 |
| Commitment shape | 24 hours x 10 generators |
| Commitment transitions | G4: 1, G7: 1 (others always on) |

### Solver Note

HiGHS cannot solve MIQP (mixed-integer quadratic programming). The quadratic cost term `marginal_cost_quadratic` was set to zero, using only linear marginal costs. Costs were differentiated across generators to create a non-trivial commitment problem.

### Built-in Constraint Types (all native)

All unit commitment constraints are built-in PyPSA attributes on the Generator component:

| Constraint | PyPSA Attribute | Type |
|-----------|-----------------|------|
| Minimum up time | `min_up_time` | Built-in |
| Minimum down time | `min_down_time` | Built-in |
| Startup cost | `start_up_cost` | Built-in |
| Shutdown cost | `shut_down_cost` | Built-in |
| Ramp rate up | `ramp_limit_up` | Built-in |
| Ramp rate down | `ramp_limit_down` | Built-in |
| Min stable generation | `p_min_pu` | Built-in |
| Committable flag | `committable` | Built-in |

No user-assembled constraints needed.

### Commitment Schedule

Extracted from `n.generators_t.status` (24x10 DataFrame of binary values).

- 8 generators committed all 24 hours
- G4 (bus 34, Pnom=508): decommitted during low-load hours
- G7 (bus 37, Pnom=564): decommitted during low-load hours

### Dispatch Profile

Load varies from 56% to 100% of base (3502-6254 MW). Dispatch tracks load profile.

## API

```python
n.generators.loc[gen, "committable"] = True
n.generators.loc[gen, "min_up_time"] = 3
# ... set other UC params ...
n.optimize(solver_name="highs", solver_options={"mip_rel_gap": 0.01})
# Results: n.generators_t.status (commitment), n.generators_t.p (dispatch)
```

## LOC

~30 lines (set snapshots, load profiles, UC parameters, solve, extract).

## Workarounds

None for the UC formulation itself. The only workaround is using linear costs instead of quadratic because HiGHS does not support MIQP. SCIP could handle MIQP but was not tested here.

## Errors

None.
