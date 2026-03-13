---
test_id: C-1
tool: pypsa
dimension: scalability
network: MEDIUM
protocol_version: "v9"
skill_version: v1
test_hash: 32a58768
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 101.458
timing_source: measured
peak_memory_mb: 2098.6
convergence_residual: null
convergence_iterations: null
loc: null
solver: null
timestamp: 2026-03-11T00:00:00Z
---

# C-1: DC Power Flow Scale

## Result: PASS

## Approach

Loaded ACTIVSg10k (10,000 buses, 9,726 lines, 2,980 transformers, 2,485 generators) via
`matpowercaseframes.CaseFrames` → pypower ppc → `n.import_from_pypower_ppc(overwrite_zero_s_nom=1.0)`.
Ran `n.lpf()` (linear/DC power flow) three times on fresh network copies and recorded wall-clock
and peak memory via `time.perf_counter()` and `tracemalloc`. Reported median solve time.

Validated nontrivial solution: 9,999/10,000 non-slack buses have nonzero angles; 9,532/9,726
lines carry nonzero flow.

## Output

| Metric | Value |
|--------|-------|
| Network | ACTIVSg10k — 10,000 buses, 9,726 lines |
| Run 1 wall-clock | 101.46 s |
| Run 2 wall-clock | 92.83 s |
| Run 3 wall-clock | 113.74 s |
| **Median solve time** | **101.46 s** |
| Min solve time | 92.83 s |
| Max solve time | 113.74 s |
| Peak memory (median) | 2,098.6 MB |
| Non-zero angles (non-slack) | 9,999 / 10,000 buses |
| Non-zero line flows | 9,532 / 9,726 lines |
| Max angle | 104.88° |
| Max line flow | 1,839.6 MW |
| Total load | 150,917 MW |

The DCPF solve is dominated by sparse matrix factorization. At ~100 s median, the 10k-bus
network is quite slow compared to specialized DCPF tools — PyPSA's `n.lpf()` builds a full
topology-based B-matrix including sub-network detection on each call.

## Workarounds

None required.

## Timing

- **Wall-clock:** 101.46 s (median of 3 runs: 92.83 / 101.46 / 113.74 s)
- **Timing source:** measured
- **Peak memory:** 2,098.6 MB
- **Solver iterations:** N/A (direct linear solve)
- **Convergence residual:** N/A (linear system)
- **CPU cores used:** 1 (single-threaded)

## Test Script

**Path:** `evaluations/pypsa/tests/scalability/test_c1_dcpf_scale.py`
