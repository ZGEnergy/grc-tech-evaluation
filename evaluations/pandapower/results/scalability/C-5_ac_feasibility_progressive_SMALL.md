---
test_id: C-5
tool: pandapower
dimension: scalability
network: SMALL
protocol_version: "v11"
skill_version: "v2"
test_hash: "1bd454bb"
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 2.22
timing_source: measured
peak_memory_mb: 27.29
convergence_residual: null
convergence_iterations: 4
convergence_evidence_quality: iteration_count_reported
loc: 300
solver: null
cpu_threads_used: 1
cpu_threads_available: 32
timestamp: "2026-03-24T00:00:00Z"
---

# C-5: AC Feasibility -- Progressive Relaxation (SMALL)

## Result: PASS

## Approach

Loaded the ACTIVSg2000 network (2000 buses, 2359 lines, 0 transformers, 484 generators) using the shared `load_pandapower` loader. Executed the progressive relaxation protocol:

1. **DCPF baseline** via `pp.rundcpp(net)` -- establishes the DC power flow solution
2. **ACPF at 0% relaxation** via `pp.runpp(net, algorithm='nr', init='dc', calculate_voltage_angles=True, tolerance_mva=1e-8, max_iteration=50)` -- uses DC warm start
3. **10% relaxation** -- prepared but not needed (0% converged)
4. **20% relaxation** -- prepared but not needed (0% converged)

pandapower's internal Newton-Raphson solver was used (no external NLP solver required). The `init='dc'` parameter provides the DC warm start automatically by running DCPF internally before the NR iteration begins. NR iteration count extracted from `net._ppc["iterations"]`.

No transformers are present in this network (the MATPOWER loader maps all branches to lines for ACTIVSg2000), so thermal relaxation applies only to line limits.

## Output

### DCPF Baseline

| Metric | Value |
|--------|-------|
| Converged | True |
| Wall-clock | 0.81 s |
| Total generation | 62,812.8 MW |
| Max line loading | 79.9% |
| Mean line loading | 30.4% |

### ACPF at 0% Relaxation

| Metric | Value |
|--------|-------|
| Converged | True |
| NR iterations | 4 |
| Wall-clock | 1.41 s |
| Voltage violations (outside [0.95, 1.05] pu) | 0 |
| Vm range | 0.972 -- 1.040 pu |
| Vm mean | 1.011 pu |
| Thermal violations (loading > 100%) | 0 |
| Max line loading | 82.7% |
| Mean line loading | 33.4% |
| Total P losses | 1,443.7 MW |

### Progressive Relaxation Summary

| Relaxation Level | Attempted | Converged |
|------------------|-----------|-----------|
| 0% | Yes | Yes |
| 10% | No (not needed) | -- |
| 20% | No (not needed) | -- |

**Relaxation level achieved:** 0% (no relaxation needed)

The ACTIVSg2000 network converges readily at 0% relaxation with a DC warm start. All voltage magnitudes are within the [0.95, 1.05] pu band, and all line loadings are below 100%. The maximum line loading increases slightly from 79.9% (DCPF) to 82.7% (ACPF) due to reactive power flows.

## Workarounds

None required.

## Timing

- **Wall-clock:** 2.22 s (DCPF + ACPF solve time, excluding network loading)
- **Timing source:** measured
- **Peak memory:** 27.29 MB (tracemalloc)
- **Solver iterations:** 4 (Newton-Raphson)
- **Convergence residual:** below 1e-8 MVA (tolerance_mva setting; pandapower does not expose exact final residual via public API)
- **CPU cores used:** 1 (pandapower NR solver is single-threaded)
- **CPU cores available:** 32

## Test Script

**Path:** `evaluations/pandapower/tests/scalability/test_c5_ac_feasibility_progressive_SMALL.py`
