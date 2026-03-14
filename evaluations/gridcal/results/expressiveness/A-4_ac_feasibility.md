---
test_id: A-4
tool: gridcal
dimension: expressiveness
network: TINY
status: pass
workaround_class: null
blocked_by: null
protocol_version: "v10"
skill_version: v1
test_hash: "8531c61c"
wall_clock_seconds: 2.78
timing_source: measured
peak_memory_mb: null
convergence_residual: 4.14e-11
convergence_iterations: 4
loc: 225
solver: "NR (native)"
timestamp: "2026-03-13T00:00:00Z"
---

# A-4: Take DC OPF dispatch from A-3, run full ACPF on that dispatch

## Result: PASS

## Approach

Loaded the IEEE 39-bus network and replicated the A-3 setup (differentiated costs + 70% branch
derating). Solved DC OPF via `vge.linear_opf()` to obtain generator dispatch. Then, **within the
same grid object** (no export/reimport), fixed each generator's active power to the DC OPF
dispatch value via `gen.P = dispatch[i]` and ran Newton-Raphson ACPF via `vge.power_flow()`.

The eval-config specifies Ipopt as solver, but GridCal has no Ipopt integration for ACPF. It uses
its own Newton-Raphson implementation (`SolverType.NR`). This is an inherent tool limitation,
not a workaround -- GridCal's native NR is the only available ACPF solver.

## Output

| Metric | Value |
|--------|-------|
| DCOPF converged | True |
| DCOPF total gen | 6,254.2 MW |
| ACPF converged | True (flat start) |
| NR iterations | 4 |
| Convergence residual | 4.14e-11 |
| Voltage range | 0.982 -- 1.064 pu |
| Total AC losses | 45.5 MW |

**Voltage violations** (outside [0.95, 1.05] pu): 5 buses

| Bus | Vm (pu) | Type |
|-----|---------|------|
| 19 | 1.0503 | over |
| 22 | 1.0501 | over |
| 25 | 1.0571 | over |
| 26 | 1.0517 | over |
| 36 | 1.0636 | over |

**Thermal violations** (loading > 100% of derated rating): 3 branches

| Branch | Loading |
|--------|---------|
| 2_3_1 | 110.6% |
| 10_32_1 | 101.6% |
| 22_35_1 | 102.9% |

The DC OPF dispatch, which uses a lossless linear approximation, produces thermal violations
when checked against the AC power flow. This is expected -- the ACPF sees reactive power flows
and losses that the DCOPF ignores. The voltage violations are all overvoltages at generator
buses, consistent with the DCOPF not modeling voltage regulation.

## Workarounds

None required. The same grid object was used for both DC OPF and ACPF without any
export/reimport step. Setting `gen.P` and calling `vge.power_flow()` achieves the
feasibility check within the same model context.

## Timing

- **Wall-clock:** 2.78 s (includes both DCOPF and ACPF)
- **Timing source:** measured
- **Peak memory:** not measured
- **NR iterations:** 4
- **Convergence residual:** 4.14e-11
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/gridcal/tests/expressiveness/test_a4_ac_feasibility.py`

Key code showing the same-model-context workflow:

```python
# Solve DC OPF
opf_results = vge.linear_opf(grid, opf_opts)
dispatch = opf_results.generator_power

# Fix dispatch on same grid — no export/reimport
for i, gen in enumerate(generators):
    gen.P = float(dispatch[i])

# Run ACPF on same grid object
pf_results = vge.power_flow(grid, options=pf_opts)

# Voltage and thermal violations directly accessible
v_mag = np.abs(pf_results.voltage)
loading = np.abs(pf_results.loading)
```
