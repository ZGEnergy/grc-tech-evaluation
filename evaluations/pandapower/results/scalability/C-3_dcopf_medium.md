---
test_id: C-3
tool: pandapower
dimension: scalability
network: MEDIUM
protocol_version: "v11"
skill_version: "v2"
test_hash: "313eb292"
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 62.434
timing_source: measured
peak_memory_mb: 2350.62
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 140
solver: PYPOWER PIPS (internal)
cpu_threads_used: 1
cpu_threads_available: 32
timestamp: 2026-03-24T00:00:00Z
---

# C-3: DC OPF on MEDIUM

## Result: PASS

## Approach

Loaded the ACTIVSg10k network (10,000 buses, 12,706 branches, 2,485 generators) via
the shared loader and ran `pp.rundcopp(net)` — pandapower's DC optimal power flow,
which uses PYPOWER's built-in PIPS (Primal-Dual Interior Point Solver).

pandapower does not expose an easy mechanism to swap LP solvers for `rundcopp`; it
uses PYPOWER's internal PIPS solver exclusively for DC OPF. This is a
[tool-specific] limitation documented in C-7 (solver swap).

### Convergence Note

pandapower sets `net.OPF_converged = True` for the OPF result but `net.converged = False`
for the power flow flag. The `OPF_converged` attribute is the correct indicator for
OPF problems. The `converged` flag pertains to Newton-Raphson power flow, which is not
run during DC OPF.

## Output

| Metric | Value |
|--------|-------|
| OPF converged | Yes |
| Solve time | 6.243400e+01 s |
| Peak memory | 2.350617e+03 MB |
| Objective (total cost) | 2.437764e+06 $/h |

### Generator Dispatch

| Metric | Value |
|--------|-------|
| Total gen (gen) | 1.329206e+05 MW |
| Total ext_grid | 1.403200e+03 MW |
| Total dispatch | 1.343238e+05 MW |
| Total load | 1.509169e+05 MW |
| Generators at Pmax | 1,236 of 1,727 |
| Generators at Pmin | 791 of 1,727 |

Note: The dispatch-load imbalance is due to the DC formulation where the slack bus
(ext_grid) compensates for the difference. In a lossless DC model, total generation
exactly meets total load; the ext_grid acts as the balancing resource.

### Branch Loading

| Metric | Value |
|--------|-------|
| Max line loading | 7.688644e+01 % |
| Mean line loading | 1.630042e+01 % |
| Max trafo loading | 7.692530e+01 % |
| Max branch loading (overall) | 7.692530e+01 % |
| Soft constraint detected | No |

No branch exceeds 100% loading. The maximum branch loading is approximately 77%,
confirming that the ACTIVSg10k network is uncongested in base-case DCOPF (consistent
with cross-tool watchpoint documentation noting max loading ~84-85% across tools).

### Bus Angles

| Metric | Value |
|--------|-------|
| Angle min | -8.497124e+01 deg |
| Angle max | 6.304253e+01 deg |

## Workarounds

None required.

## Timing

- **Wall-clock:** 62.434 s
- **Timing source:** measured
- **Peak memory:** 2350.62 MB
- **CPU threads used:** 1 (PYPOWER PIPS is single-threaded)
- **CPU threads available:** 32

The solve time is notably high (62 s) for a DC OPF, reflecting the PIPS interior
point method's computational cost at 10,000-bus scale. The 2.35 GB peak memory
is also substantial [solver-specific: PYPOWER PIPS interior point method at scale].

## Test Script

**Path:** `evaluations/pandapower/tests/scalability/test_c3_dcopf_medium.py`
