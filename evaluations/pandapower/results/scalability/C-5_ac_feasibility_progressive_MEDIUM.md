---
test_id: C-5
tool: pandapower
dimension: scalability
network: MEDIUM
protocol_version: "v11"
skill_version: "v2"
test_hash: "1bd454bb"
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 2.77
timing_source: measured
peak_memory_mb: 39.40
convergence_residual: null
convergence_iterations: 5
convergence_evidence_quality: iteration_count_reported
loc: 265
solver: null
cpu_threads_used: 1
cpu_threads_available: 32
timestamp: "2026-03-24T00:00:00Z"
---

# C-5: AC Feasibility -- Progressive Relaxation (MEDIUM)

## Result: PASS

## Approach

Loaded the ACTIVSg10k network (10,000 buses, 9,726 lines, 975 transformers, 1,727 generators) using the shared `load_pandapower` loader. Executed the progressive relaxation protocol:

1. **DCPF baseline** via `pp.rundcpp(net)` -- establishes the DC power flow solution
2. **ACPF at 0% relaxation** via `pp.runpp(net, algorithm='nr', init='dc', calculate_voltage_angles=True, tolerance_mva=1e-8, max_iteration=100, lightsim2grid=True)` -- uses DC warm start with lightsim2grid acceleration
3. **10% relaxation** -- prepared but not needed (0% converged)
4. **20% relaxation** -- prepared but not needed (0% converged)

pandapower's internal Newton-Raphson solver was used with `lightsim2grid=True` for acceleration on this larger network. The `init='dc'` parameter provides the DC warm start automatically. NR iteration count extracted from `net._ppc["iterations"]`.

**Note:** lightsim2grid acceleration showed negligible speedup at this scale -- 1.53 s with lightsim2grid vs 1.48 s without. This suggests the bottleneck is in pandapower's Python-level pre/post-processing rather than the NR linear algebra kernel.

## Output

### DCPF Baseline

| Metric | Value |
|--------|-------|
| Converged | True |
| Wall-clock | 1.24 s |
| Total generation | 134,235.8 MW |
| Max line loading | 77.0% |

### ACPF at 0% Relaxation

| Metric | Value |
|--------|-------|
| Converged | True |
| NR iterations | 5 |
| Wall-clock | 1.53 s |
| lightsim2grid used | True |
| Voltage violations low (Vm < 0.95 pu) | 426 |
| Voltage violations high (Vm > 1.05 pu) | 86 |
| Total voltage violations | 512 |
| Vm range | 0.868 -- 1.081 pu |
| Vm mean | 1.004 pu |
| Line thermal violations (loading > 100%) | 42 |
| Max line loading | 1,523.6% |
| Transformer thermal violations (loading > 100%) | 2 |
| Max trafo loading | 123.3% |
| Total P losses | 2,598.7 MW |

### Progressive Relaxation Summary

| Relaxation Level | Attempted | Converged |
|------------------|-----------|-----------|
| 0% | Yes | Yes |
| 10% | No (not needed) | -- |
| 20% | No (not needed) | -- |

**Relaxation level achieved:** 0% (no relaxation needed)

The ACTIVSg10k network converges at 0% relaxation with a DC warm start, but the converged solution reveals significant violations:

- **512 voltage violations** (426 low, 86 high) -- the Vm range extends to 0.868 pu (well below the 0.95 pu threshold) and 1.081 pu (above 1.05 pu). This is expected for a network of this size with diverse voltage levels.
- **42 line thermal violations** with a maximum loading of 1,523.6% -- this extreme value suggests some lines have very low rated current in the MATPOWER source data relative to the flows they carry under AC conditions.
- **2 transformer thermal violations** with max loading of 123.3%.

These violations are informational findings, not test failures -- C-5 is a diagnostic test. The key finding is that the network converges readily without relaxation, despite producing a solution with violations that would require mitigation in an operational context.

## Workarounds

None required.

## Timing

- **Wall-clock:** 2.77 s (DCPF 1.24 s + ACPF 1.53 s, excluding network loading)
- **Timing source:** measured
- **Peak memory:** 39.40 MB (tracemalloc)
- **Solver iterations:** 5 (Newton-Raphson)
- **Convergence residual:** below 1e-8 MVA (tolerance_mva setting; pandapower does not expose exact final residual via public API)
- **CPU cores used:** 1 (pandapower NR solver is single-threaded)
- **CPU cores available:** 32

### lightsim2grid Comparison

| Backend | ACPF Solve Time (s) | NR Iterations |
|---------|---------------------|---------------|
| lightsim2grid | 1.53 | 5 |
| pandapower native | 1.48 | 5 |

lightsim2grid provides no measurable speedup on ACTIVSg10k. The NR linear algebra kernel is not the bottleneck at this scale.

## Test Script

**Path:** `evaluations/pandapower/tests/scalability/test_c5_ac_feasibility_progressive_MEDIUM.py`
