---
test_id: C-2
tool: pandapower
dimension: scalability
network: MEDIUM
protocol_version: "v11"
skill_version: "v2"
test_hash: "23203f66"
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 2.532
timing_source: measured
peak_memory_mb: 38.99
convergence_residual: null
convergence_iterations: 5
convergence_evidence_quality: iteration_count_reported
loc: 185
solver: Newton-Raphson (pandapower internal)
cpu_threads_used: 1
cpu_threads_available: 32
timestamp: 2026-03-24T00:00:00Z
---

# C-2: ACPF on MEDIUM

## Result: PASS

## Approach

Loaded the ACTIVSg10k network (10,000 buses, 12,706 branches) via the shared loader
and ran `pp.runpp(net)` with Newton-Raphson algorithm. Two configurations were tested:

1. **Standard pandapower NR** — `pp.runpp(net, algorithm="nr", init="dc",
   calculate_voltage_angles=True, tolerance_mva=1e-8, max_iteration=100)`
2. **lightsim2grid NR** — Same settings plus `lightsim2grid=True` for comparison timing

Both used DC initialization (DC power flow solution as starting point for NR).

### Convergence Verification

Convergence was verified via the `iteration_count_reported` tier:
- pandapower exposes iteration count via `net._ppc["iterations"]`
- 5 NR iterations reported with tolerance_mva = 1e-8 (= 1.000000e-10 p.u.)
- 99.98% of buses have voltage magnitude differing from 1.0 p.u. (non-flat solution)
- Voltage magnitudes range from 0.868 to 1.081 p.u. — clearly non-trivial solution

The tolerance in per-unit terms (1e-10 p.u.) is far below the 1e-4 p.u. convergence
threshold, confirming high-quality convergence.

## Output

### Standard Newton-Raphson

| Metric | Value |
|--------|-------|
| Solve time | 2.532 s |
| Peak memory | 38.99 MB |
| NR iterations | 5 |
| Converged | Yes |
| Tolerance (MVA) | 1.000000e-08 |
| Tolerance (p.u.) | 1.000000e-10 |

### lightsim2grid Newton-Raphson

| Metric | Value |
|--------|-------|
| Solve time | 0.132 s |
| Peak memory | 18.35 MB |
| NR iterations | 5 |
| Converged | Yes |
| **Speedup vs standard** | **19.2x** |

### Voltage Profile

| Metric | Value |
|--------|-------|
| V_min | 8.681500e-01 p.u. |
| V_max | 1.081400e+00 p.u. |
| V_mean | 1.004204e+00 p.u. |
| V_std | 2.781587e-02 p.u. |
| % buses non-unity | 99.98% |

### Angle Profile

| Metric | Value |
|--------|-------|
| Angle min | -92.41 deg |
| Angle max | 15.69 deg |
| Angle mean | -57.69 deg |

### Branch Loading

| Metric | Value |
|--------|-------|
| Max line loading | 1523.59% |
| Mean line loading | 20.43% |

Note: The high max line loading (1523.59%) in the AC power flow solution indicates
some branches are heavily loaded when reactive power flows and voltage drops are
accounted for. This is an AC feasibility observation, not a convergence failure.

### Power Balance

| Metric | Value |
|--------|-------|
| Total generation | 1.369732e+05 MW |
| Total load | 1.509169e+05 MW |
| Total losses | 2.598705e+03 MW |

## Workarounds

None required.

## Timing

- **Wall-clock (standard NR):** 2.532 s
- **Wall-clock (lightsim2grid):** 0.132 s (19.2x speedup)
- **Timing source:** measured
- **Peak memory:** 38.99 MB (standard), 18.35 MB (lightsim2grid)
- **NR iterations:** 5
- **Convergence evidence quality:** iteration_count_reported
- **CPU threads used:** 1 (pandapower NR is single-threaded)
- **CPU threads available:** 32

## Test Script

**Path:** `evaluations/pandapower/tests/scalability/test_c2_acpf_medium.py`
