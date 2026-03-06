# B-7: AC Feasibility Extension — DC OPF Dispatch to AC PF Check (TINY)

- **Test ID:** B-7
- **Slug:** ac_feasibility_extension
- **Tool:** PyPSA 1.1.2
- **Network:** IEEE 39-bus (case39.m)
- **Solver:** HiGHS 1.13.1 (DC OPF) + Newton-Raphson (ACPF)
- **Status:** PASS
- **Workaround durability:** Stable

## Pass Condition

DC OPF dispatch -> fix generators -> run AC PF -> check violations.
All within same model context.

## Results

| Metric | Value |
|--------|-------|
| DC OPF solve time | 0.355 s |
| AC PF solve time | 0.089 s |
| Total wall clock | 0.444 s |
| ACPF converged | Yes (4 iterations) |
| Voltage violations | 1 (bus 36: 1.064 pu > 1.06 limit) |
| Thermal violations | 0 |
| LOC | ~15 lines |

### Workflow

1. Solve DC OPF: `n.optimize(solver_name="highs")` -- gets optimal dispatch
2. Fix generators: `n.generators.loc[gen, "p_set"] = dispatch_value` for each generator
3. Run AC PF: `n.pf()` -- Newton-Raphson converges in 4 iterations
4. Check violations: read `n.buses_t.v_mag_pu` and `n.lines_t.p0/q0`

### Same-Model Context

The entire workflow executes on a single `pypsa.Network` object. No export to file or reimport is needed. The generator control types (`Slack`, `PV`) are already set correctly from the MATPOWER import, so the AC PF runs with appropriate bus control types.

### Voltage Violation Detail

| Bus | V magnitude (pu) | Limit (pu) | Type |
|-----|------------------|------------|------|
| 36 | 1.0636 | 1.06 | Overvoltage |

Voltage range across all buses: 0.982 - 1.064 pu.

## API

```python
# Step 1: DC OPF
n.optimize(solver_name="highs", ...)

# Step 2: Fix dispatch
for gen in n.generators.index:
    n.generators.loc[gen, "p_set"] = n.generators_t.p.iloc[0][gen]

# Step 3: AC PF
n.pf()

# Step 4: Check violations
v_mag = n.buses_t.v_mag_pu.iloc[0]
line_p = n.lines_t.p0.iloc[0]
line_q = n.lines_t.q0.iloc[0]
```

## Workaround Assessment

Setting `p_set` on generators is a standard PyPSA pattern, not truly a workaround. The generator control types from MATPOWER import correctly distinguish slack (angle reference) from PV (voltage-controlled) generators. The workflow is natural and documented.

**Durability: Stable** -- uses only documented public API.

## Test Script

`evaluations/pypsa/tests/extensibility/test_b7_ac_feasibility_extension_tiny.py`
