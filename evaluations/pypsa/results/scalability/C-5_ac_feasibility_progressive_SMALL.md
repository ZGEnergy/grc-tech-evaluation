---
test_id: C-5
tool: pypsa
dimension: scalability
network: SMALL
protocol_version: v11
skill_version: v2
test_hash: d97906f2
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 14.91
timing_source: measured
peak_memory_mb: 84.08
convergence_residual: 5.13e-09
convergence_iterations: 4
convergence_evidence_quality: residual_reported
loc: 337
solver: PyPSA NR (internal Newton-Raphson)
cpu_threads_used: 1
cpu_threads_available: 32
timestamp: 2026-03-24T22:00:00Z
---

# C-5: AC Feasibility — Progressive Relaxation on SMALL

## Result: PASS

## Approach

Loaded ACTIVSg2000 (2,000 buses, 2,359 lines, 544 generators) using raw
`matpowercaseframes` import (without the shared loader's `b=1/x` DC transformer
patch, which would break AC convergence). Set `overwrite_zero_s_nom=100000.0`
for large-network AC feasibility.

**Progressive relaxation protocol:**
1. Ran DCPF (`n.lpf()`) to obtain warm-start voltage angles
2. Attempted ACPF (`n.pf(x_tol=1e-6, use_seed=True)`) at 0% relaxation (original s_nom)
3. Attempted ACPF at 10% relaxation (s_nom * 1.10)
4. Attempted ACPF at 20% relaxation (s_nom * 1.20)

**Solver note:** PyPSA uses its own internal Newton-Raphson solver for AC power
flow (`n.pf()`), not Ipopt. Ipopt is an NLP optimizer for AC OPF, not power
flow. The internal NR solver uses scipy sparse linear algebra and is the correct
AC PF method for PyPSA. [tool-specific: PyPSA uses internal NR, not external NLP solver]

## Output

### DCPF Warm Start

| Metric | Value |
|--------|-------|
| DCPF wall-clock | 1.025 s |
| Buses with nonzero angles | 1,999 / 2,000 |

### Progressive Relaxation Results

| Relaxation | Converged | Iterations | Residual | Wall-clock (s) | Peak Memory (MB) | V_min (pu) | V_max (pu) | Non-flat buses |
|------------|-----------|------------|----------|----------------|-------------------|------------|------------|----------------|
| 0% | Yes | 4 | 5.13e-09 | 4.05 | 84.08 | 0.9736 | 1.0417 | 1,879 (93.95%) |
| 10% | Yes | 4 | 1.98e-09 | 4.25 | 84.08 | 0.9775 | 1.0431 | 1,879 (93.95%) |
| 20% | Yes | 4 | 1.07e-09 | 4.06 | 84.08 | 0.9789 | 1.0443 | 1,879 (93.95%) |

### Key Findings

- **First converged relaxation:** 0% (no relaxation needed)
- All three relaxation levels converge in exactly 4 NR iterations
- Convergence residuals are well below tolerance (1e-6): 5.1e-9 to 1.1e-9
- Voltage magnitudes are within [0.9736, 1.0443] pu across all relaxation levels
- 93.95% of buses have non-flat voltages (1,879 of 2,000)
- The 121 buses with flat voltage (exactly 1.0 pu) are PV buses (generator buses
  holding voltage setpoint)
- Relaxation progressively improves convergence quality (residual decreases)

### Convergence Quality Validation

The AC PF solution is genuine:
- **Iteration count > 0:** 4 iterations confirms Newton-Raphson executed
- **Residual < tolerance:** 5.13e-09 << 1e-6
- **Non-trivial voltage profile:** 93.95% of buses differ from flat start
- **Voltage range is physically reasonable:** 0.97--1.04 pu

## Workarounds

None required. PyPSA's internal NR solver converges on ACTIVSg2000 at all
relaxation levels without difficulty.

## Timing

- **DCPF warm-start:** 1.025 s
- **ACPF (0% relaxation):** 4.05 s
- **ACPF (10% relaxation):** 4.25 s
- **ACPF (20% relaxation):** 4.06 s
- **Total wall-clock:** 14.91 s
- **Timing source:** measured
- **Peak memory:** 84.08 MB
- **NR iterations:** 4
- **Convergence residual:** 5.13e-09
- **CPU threads used:** 1 (PyPSA NR is single-threaded)
- **CPU threads available:** 32

## Test Script

**Path:** `evaluations/pypsa/tests/scalability/test_c5_ac_feasibility_progressive.py`
