# A-6: SCED -- Fix Commitment, Solve Economic Dispatch (TINY)

- **Test ID:** A-6
- **Slug:** sced
- **Tool:** PyPSA 1.1.2
- **Network:** IEEE 39-bus (case39.m)
- **Solver:** HiGHS 1.13.1
- **Status:** PASS

## Pass Condition

UC and ED cleanly separable as two-stage workflow. Ramp rate constraints demonstrably enforced in ED stage.

## Results

| Metric | Value |
|--------|-------|
| Stage 1 (SCUC) wall clock | 1.448 s |
| Stage 2 (ED) wall clock | 0.373 s |
| Total wall clock | 1.822 s |
| Stage 1 objective | 118501.49 (MILP) |
| Stage 2 objective | 117245.29 (LP) |
| Ramp violations in ED | 0 |
| Generators decommitted | G4 (5 hrs), G7 (22 hrs) |
| Dispatch when OFF | 0.0 MW (correct) |

### Two-Stage Workflow

**Stage 1 -- SCUC (Unit Commitment as MILP):**
- All generators set with `committable=True`, `min_up_time=3`, `min_down_time=2`, `ramp_limit_up/down=0.3`, `p_min_pu=0.2`
- Solved with HiGHS at 1% MIP gap tolerance (achieved 0.097%)
- Commitment schedule extracted from `n.generators_t.status`

**Stage 2 -- ED (Economic Dispatch as LP):**
- Commitment fixed by setting `committable=False`
- Time-varying bounds from commitment: `p_min_pu = status * 0.2`, `p_max_pu = status * 1.0`
- Ramp limits preserved from Stage 1 (not removed by `committable=False`)
- Re-solved as LP (no binary variables)

The ED objective (117,245) is lower than the SCUC objective (118,501) because startup/shutdown costs are no longer incurred and the LP relaxation is tighter than the MIP solution.

### Ramp Rate Enforcement

All 10 generators respect ramp limits (30% of p_nom per hour) in the ED stage. Sample verification:

| Generator | p_nom | Ramp limit (MW) | Max ramp up (MW) | Max ramp down (MW) | OK |
|-----------|-------|-----------------|-------------------|---------------------|-----|
| G0 | 1040 | 312.0 | 66.9 | -55.8 | Yes |
| G2 | 725 | 217.5 | 217.5 | -217.5 | Yes |
| G6 | 580 | 174.0 | 174.0 | -174.0 | Yes |
| G9 | 1100 | 330.0 | 330.0 | -257.3 | Yes |

G2, G6, and G9 hit their ramp limits exactly at some hours, confirming the constraints are binding and enforced.

### Commitment Fixation Verification

- G4 (p_nom=508): OFF for 5 hours, dispatch = 0.0 MW during those hours
- G7 (p_nom=564): OFF for 22 hours, dispatch = 0.0 MW during those hours
- All other generators committed for all 24 hours

### Hourly Dispatch Profile

Dispatch tracks the sinusoidal load profile from 3,502 MW (hour 4, 56% load) to 6,254 MW (hours 11 and 18, 100% load).

## API

```python
# Stage 1: SCUC
n.generators["committable"] = True
n.optimize(solver_name="highs", solver_options={"mip_rel_gap": 0.01})
commitment = n.generators_t.status.copy()

# Stage 2: Fix commitment, solve ED
for gen in n.generators.index:
    n.generators.loc[gen, "committable"] = False
    n.generators_t.p_min_pu[gen] = commitment[gen] * 0.2
    n.generators_t.p_max_pu[gen] = commitment[gen] * 1.0
n.optimize(solver_name="highs")  # now LP
```

## LOC

~40 lines (setup UC, solve SCUC, fix commitment, solve ED, verify ramps).

## Workarounds

1. **Manual commitment fixation (stable):** PyPSA has no built-in "fix commitment and re-dispatch" method. The user must manually set `committable=False` and use time-varying `p_min_pu`/`p_max_pu` to encode the commitment schedule. This is a well-documented pattern but requires understanding PyPSA's per-unit time-series convention. Setting `p_max_pu=0` for OFF hours and `p_min_pu=0.2` for ON hours achieves the desired behavior.

## Errors

None.
