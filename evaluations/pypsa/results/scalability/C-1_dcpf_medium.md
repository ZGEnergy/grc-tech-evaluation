---
test_id: C-1
tool: pypsa
dimension: scalability
network: MEDIUM
protocol_version: v11
skill_version: v2
test_hash: 55a19ddd
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 22.18
timing_source: measured
peak_memory_mb: 2098.58
cpu_threads_used: 1
cpu_threads_available: 32
loc: 144
solver: null
timestamp: 2026-03-24T17:30:00Z
---

# C-1: DCPF on MEDIUM

## Result: PASS

## Approach

Loaded ACTIVSg10k (10,000 buses, 9,726 lines, 2,980 transformers, 2,485 generators)
via the shared `matpower_loader.load_pypsa()` function, which applies branch status,
transformer susceptance, and gencost patches. Ran `n.lpf()` three times on fresh
copies and reported the median wall-clock time.

PyPSA's `n.lpf()` performs a direct linear power flow solve (B-matrix factorization)
with no iterative solver. Single-threaded execution.

## Output

| Metric | Value |
|--------|-------|
| Buses | 10,000 |
| Lines | 9,726 |
| Transformers | 2,980 |
| Generators | 2,485 |
| Total load | 150,917 MW |

### Timing (3 runs)

| Run | Wall-clock (s) | Peak Memory (MB) |
|-----|----------------|-------------------|
| 1 | 22.162 | 2,098.8 |
| 2 | 22.504 | 2,098.6 |
| 3 | 22.176 | 2,098.6 |
| **Median** | **22.176** | **2,098.6** |

### Validation

| Metric | Value |
|--------|-------|
| Non-zero angles (non-slack) | 9,999 / 10,000 |
| Non-zero line flows | 9,532 / 9,726 |
| Max voltage angle | 104.88 deg |
| Max line flow | 1,839.6 MW |

The DCPF produced a nontrivial solution: 99.99% of non-slack buses have nonzero
voltage angles and 98.0% of lines carry nonzero flow.

## Workarounds

None required.

## Timing

- **Wall-clock (median of 3):** 22.18 s
- **Timing source:** measured
- **Peak memory:** 2,098.58 MB
- **CPU threads used:** 1 (n.lpf() is single-threaded)
- **CPU threads available:** 32

## Test Script

**Path:** `evaluations/pypsa/tests/scalability/test_c1_dcpf_medium.py`
