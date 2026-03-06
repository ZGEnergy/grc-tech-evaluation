# A-4: AC PF Feasibility Check on DC OPF Dispatch (TINY)

- **Test ID:** A-4
- **Slug:** ac_feasibility
- **Tool:** PyPSA 1.1.2
- **Network:** IEEE 39-bus (case39.m)
- **Solver:** HiGHS 1.13.1 (DC OPF), Newton-Raphson (AC PF)
- **Status:** PASS

## Pass Condition

Achievable within same model context (no file export/reimport). Voltage and thermal violations identifiable.

## Results

| Metric | Value |
|--------|-------|
| DC OPF wall clock | 0.335 s |
| AC PF wall clock | 0.089 s |
| DC OPF objective | 41261.94 |
| DC OPF total dispatch | 6254.23 MW |
| AC PF convergence | Flat start converged (no fallback needed) |
| Voltage violations | 5 buses |
| Thermal violations | 0 lines |
| Max line loading | 89.2% |
| AC line losses | 34.79 MW |

### Same-Model Workflow

The entire workflow runs on a single `pypsa.Network` object with no file export or reimport:

1. `n.optimize(solver_name="highs")` -- DC OPF
2. Set `n.generators.p_set` from `n.generators_t.p` dispatch results
3. `n.pf()` -- AC power flow

This is a clean, in-memory two-step workflow.

### Voltage Violations (|v_mag_pu - 1.0| > 0.05)

| Bus | v_mag_pu | Deviation |
|-----|----------|-----------|
| 25 | 1.0534 | 0.0534 |
| 26 | 1.0528 | 0.0528 |
| 28 | 1.0536 | 0.0536 |
| 29 | 1.0532 | 0.0532 |
| 36 | 1.0636 | 0.0636 |

All violations are overvoltage (v > 1.05 pu), concentrated in the generator-bus area (buses 25-29, 36). This is expected: DC OPF ignores reactive power and voltage setpoints, so the AC feasibility check reveals voltage regulation issues.

### Thermal Violations

No line or transformer thermal violations detected. Maximum line loading is 89.2% of s_nom.

### Voltage Range

- Minimum: 0.982 pu
- Maximum: 1.064 pu
- Angle range: -19.79 deg to +5.93 deg

## API

```python
# Stage 1: DC OPF
n.optimize(solver_name="highs")
dc_dispatch = n.generators_t.p.iloc[0]

# Stage 2: Fix dispatch, run AC PF (same object)
for gen in n.generators.index:
    n.generators.loc[gen, "p_set"] = dc_dispatch[gen]
n.pf()

# Identify violations
v_deviation = (n.buses_t.v_mag_pu.iloc[0] - 1.0).abs()
voltage_violations = v_deviation[v_deviation > 0.05]
s_apparent = np.sqrt(n.lines_t.p0.iloc[0]**2 + n.lines_t.q0.iloc[0]**2)
thermal_violations = s_apparent[s_apparent > n.lines.s_nom]
```

## LOC

~20 lines beyond network loading (DC OPF, set p_set, AC PF, violation checks).

## Workarounds

None. The workflow is natively supported.

## Errors

None.
