---
test_id: C-2
tool: pypsa
dimension: scalability
network: MEDIUM
protocol_version: v11
skill_version: v2
test_hash: 474071eb
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 21.66
timing_source: measured
peak_memory_mb: 2098.58
convergence_residual: 1.858352e-09
convergence_iterations: 5
convergence_evidence_quality: residual_reported
cpu_threads_used: 1
cpu_threads_available: 32
loc: 196
solver: PyPSA NR (internal Newton-Raphson)
timestamp: 2026-03-24T17:30:00Z
---

# C-2: ACPF on MEDIUM

## Result: PASS

## Approach

Loaded ACTIVSg10k (10,000 buses, 9,726 lines, 2,485 generators) using raw
`matpowercaseframes` import (without the shared loader's `b=1/x` DC transformer
patch, which is not appropriate for AC power flow). Set `overwrite_zero_s_nom=100000.0`
for large-network AC feasibility.

Used DCPF warm start via `n.lpf()` (5.81s), then ran `n.pf(x_tol=1e-6, use_seed=True)`
for Newton-Raphson AC power flow. PyPSA uses its own internal scipy-based NR solver,
not Ipopt.

## Output

| Metric | Value |
|--------|-------|
| Converged | Yes |
| NR iterations | 5 |
| Final residual | 1.858e-09 |
| Max bus mismatch | < 1e-4 p.u. (residual 1.86e-9 << threshold) |
| V_min | 0.9568 p.u. |
| V_max | 1.0956 p.u. |
| Non-flat buses | 9,998 / 10,000 (99.98%) |
| Max voltage angle | 66.62 deg |

### Convergence Quality Validation

- **Iteration count > 0:** 5 iterations confirms Newton-Raphson executed
- **Residual < threshold:** 1.858e-09 << 1e-4 p.u. threshold
- **Non-trivial voltage profile:** 99.98% of buses differ from flat start
- **Voltage range physically reasonable:** 0.957--1.096 p.u.
- **Evidence tier:** `residual_reported` (highest quality)

### DCPF Warm Start

| Metric | Value |
|--------|-------|
| DCPF wall-clock | 5.81 s |
| DCPF nonzero angles | 9,999 / 10,000 |

## Workarounds

None required. Raw import (without DC transformer patch) is the standard approach
for AC power flow — the shared loader's susceptance patch `b=1/x` is specific to
DC analysis.

## Timing

- **DCPF warm-start:** 5.81 s
- **ACPF solve:** 21.66 s
- **Timing source:** measured
- **Peak memory:** 2,098.58 MB
- **NR iterations:** 5
- **Convergence residual:** 1.858e-09
- **CPU threads used:** 1 (n.pf() is single-threaded NR)
- **CPU threads available:** 32

## Test Script

**Path:** `evaluations/pypsa/tests/scalability/test_c2_acpf_medium.py`
