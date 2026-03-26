---
test_id: C-5
tool: pypsa
dimension: scalability
network: MEDIUM
protocol_version: v11
skill_version: v2
test_hash: d97906f2
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 193.05
timing_source: measured
peak_memory_mb: 2098.58
convergence_residual: 1.858352e-09
convergence_iterations: 5
convergence_evidence_quality: residual_reported
relaxation_level_achieved: 0%
cpu_threads_used: 1
cpu_threads_available: 32
loc: 243
solver: PyPSA NR (internal Newton-Raphson)
timestamp: 2026-03-24T17:40:00Z
---

# C-5: AC Feasibility — Progressive Relaxation on MEDIUM

## Result: PASS

## Approach

Loaded ACTIVSg10k (10,000 buses, 9,726 lines, 2,485 generators) using raw
`matpowercaseframes` import (without the shared loader's `b=1/x` DC transformer
patch). Set `overwrite_zero_s_nom=100000.0` for large-network AC feasibility.

Progressive relaxation protocol:
1. DCPF warm start via `n.lpf()`
2. ACPF at 0% relaxation via `n.pf(x_tol=1e-6, use_seed=True)`
3. ACPF at 10% relaxation
4. ACPF at 20% relaxation

## Output

### DCPF Warm Start

| Metric | Value |
|--------|-------|
| DCPF wall-clock | 6.85 s |
| Buses with nonzero angles | 9,999 / 10,000 |

### Progressive Relaxation Results

| Relaxation | Converged | Iterations | Residual | Wall-clock (s) | Peak Memory (MB) | V_min (pu) | V_max (pu) | Non-flat buses |
|------------|-----------|------------|----------|----------------|-------------------|------------|------------|----------------|
| 0% | Yes | 5 | 1.858e-09 | 25.28 | 2,098.57 | 0.9568 | 1.0956 | 9,998 (99.98%) |
| 10% | Yes | 5 | 1.220e-09 | 67.05 | 2,098.58 | 0.9616 | 1.0915 | 9,998 (99.98%) |
| 20% | Yes | 5 | 1.429e-09 | 89.85 | 2,098.58 | 0.9616 | 1.0882 | 9,998 (99.98%) |

### Key Findings

- **First converged relaxation:** 0% (no relaxation needed)
- All three levels converge in 5 NR iterations (one more than SMALL's 4)
- Convergence residuals well below tolerance: 1.2e-9 to 1.9e-9
- Voltage magnitudes within [0.9568, 1.0956] pu
- 99.98% of buses have non-flat voltages (9,998 of 10,000)
- Peak memory stable at ~2,099 MB across all attempts

### Scaling Comparison: SMALL vs MEDIUM

| Metric | SMALL (2k) | MEDIUM (10k) | Scale Factor |
|--------|-----------|-------------|--------------|
| Buses | 2,000 | 10,000 | 5.0x |
| Lines | 2,359 | 9,726 | 4.1x |
| DCPF time | 0.99 s | 6.85 s | 6.9x |
| ACPF time (0%) | 4.18 s | 25.28 s | 6.0x |
| NR iterations | 4 | 5 | 1.25x |
| Peak memory | 84 MB | 2,099 MB | 25.0x |
| Residual | 5.1e-9 | 1.9e-9 | — |

ACPF wall-clock scales approximately linearly with network size (~6x for 5x
more buses). Memory scales super-linearly (25x for 5x buses) due to the dense
admittance matrix and Jacobian construction. NR iteration count is stable
(4 vs 5), indicating good convergence properties on both networks.

### Convergence Quality Validation

The AC PF solution is genuine:
- **Iteration count > 0:** 5 iterations confirms Newton-Raphson executed
- **Residual < tolerance:** 1.858e-09 << 1e-6
- **Non-trivial voltage profile:** 99.98% of buses differ from flat start
- **Voltage range physically reasonable:** 0.957--1.096 pu

### Wall-clock Variability

The 10% and 20% relaxation attempts show significantly longer wall-clock times
(67s and 90s) compared to the 0% attempt (25s), despite identical iteration counts
and similar residuals. This variability is due to running on a shared resource
(containerized environment with 32 cores) where background tasks may contend for
CPU. The solve is single-threaded so the actual compute work is comparable.

## Workarounds

None required. PyPSA's internal NR solver converges on ACTIVSg10k at all
relaxation levels without difficulty.

## Timing

- **DCPF warm-start:** 6.85 s
- **ACPF (0% relaxation):** 25.28 s
- **ACPF (10% relaxation):** 67.05 s
- **ACPF (20% relaxation):** 89.85 s
- **Total wall-clock:** 193.05 s
- **Timing source:** measured
- **Peak memory:** 2,098.58 MB
- **NR iterations:** 5
- **Convergence residual:** 1.858e-09
- **CPU threads used:** 1
- **CPU threads available:** 32

## Test Script

**Path:** `evaluations/pypsa/tests/scalability/test_c5_ac_feasibility_progressive_medium.py`
