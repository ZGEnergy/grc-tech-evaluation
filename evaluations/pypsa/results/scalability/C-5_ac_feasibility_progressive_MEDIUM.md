---
test_id: C-5
tool: pypsa
dimension: scalability
network: MEDIUM
protocol_version: v10
skill_version: v1
test_hash: 5a5b387a
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 86.74
timing_source: measured
peak_memory_mb: 2098.58
convergence_residual: 1.86e-09
convergence_iterations: 5
loc: 342
solver: PyPSA NR (internal Newton-Raphson)
timestamp: 2026-03-14T01:40:00Z
---

# C-5: AC Feasibility — Progressive Relaxation on MEDIUM

## Result: PASS

## Approach

Loaded ACTIVSg10k (10,000 buses, 9,726 lines, 2,485 generators) using raw
`matpowercaseframes` import (without the shared loader's `b=1/x` DC transformer
patch). Set `overwrite_zero_s_nom=100000.0` for large-network AC feasibility.

Same progressive relaxation protocol as SMALL:
1. DCPF warm start via `n.lpf()`
2. ACPF at 0%, 10%, 20% relaxation via `n.pf(x_tol=1e-6, use_seed=True)`

## Output

### DCPF Warm Start

| Metric | Value |
|--------|-------|
| DCPF wall-clock | 4.96 s |
| Buses with nonzero angles | 9,999 / 10,000 |

### Progressive Relaxation Results

| Relaxation | Converged | Iterations | Residual | Wall-clock (s) | Peak Memory (MB) | V_min (pu) | V_max (pu) | Non-flat buses |
|------------|-----------|------------|----------|----------------|-------------------|------------|------------|----------------|
| 0% | Yes | 5 | 1.86e-09 | 19.12 | 2,098.57 | 0.9568 | 1.0956 | 9,998 (99.98%) |
| 10% | Yes | 5 | 1.22e-09 | 19.33 | 2,098.58 | 0.9616 | 1.0915 | 9,998 (99.98%) |
| 20% | Yes | 5 | 1.43e-09 | 19.53 | 2,098.57 | 0.9616 | 1.0882 | 9,998 (99.98%) |

### Key Findings

- **First converged relaxation:** 0% (no relaxation needed)
- All three levels converge in 5 NR iterations (one more than SMALL)
- Convergence residuals are well below tolerance: 1.2e-9 to 1.9e-9
- Voltage magnitudes are within [0.9568, 1.0956] pu — wider range than SMALL
  as expected for a larger, more complex network
- 99.98% of buses have non-flat voltages (9,998 of 10,000)
- Peak memory is 2,098 MB (~2.1 GB), a significant increase from SMALL (84 MB)

### Scaling Comparison: SMALL vs MEDIUM

| Metric | SMALL (2k) | MEDIUM (10k) | Scale Factor |
|--------|-----------|-------------|--------------|
| Buses | 2,000 | 10,000 | 5.0x |
| Lines | 2,359 | 9,726 | 4.1x |
| DCPF time | 0.99 s | 4.96 s | 5.0x |
| ACPF time (0%) | 4.18 s | 19.12 s | 4.6x |
| NR iterations | 4 | 5 | 1.25x |
| Peak memory | 84 MB | 2,099 MB | 25.0x |
| Residual | 5.1e-9 | 1.9e-9 | - |

ACPF wall-clock scales approximately linearly with network size (~4.6x for 5x
more buses). Memory scales super-linearly (25x for 5x buses) due to the dense
admittance matrix and Jacobian construction. NR iteration count is stable
(4 vs 5), indicating good convergence properties on both networks.

### Convergence Quality Validation

The AC PF solution is genuine:
- **Iteration count > 0:** 5 iterations confirms Newton-Raphson executed
- **Residual < tolerance:** 1.86e-09 << 1e-6
- **Non-trivial voltage profile:** 99.98% of buses differ from flat start
- **Voltage range is physically reasonable:** 0.96--1.10 pu (wider than SMALL
  due to larger network with more voltage variation)

## Workarounds

None required. PyPSA's internal NR solver converges on ACTIVSg10k at all
relaxation levels without difficulty.

## Timing

- **DCPF warm-start:** 4.96 s
- **ACPF (0% relaxation):** 19.12 s
- **ACPF (10% relaxation):** 19.33 s
- **ACPF (20% relaxation):** 19.53 s
- **Total wall-clock:** 86.74 s
- **Timing source:** measured
- **Peak memory:** 2,098.58 MB
- **NR iterations:** 5
- **Convergence residual:** 1.86e-09

## Test Script

**Path:** `evaluations/pypsa/tests/scalability/test_c5_ac_feasibility_progressive.py`
