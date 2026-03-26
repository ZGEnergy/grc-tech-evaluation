---
test_id: B-9
tool: matpower
dimension: extensibility
network: TINY
protocol_version: "v11"
skill_version: "v2"
test_hash: "d8e7210b"
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 0.2853
timing_source: measured
peak_memory_mb: 1.8
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 169
solver: null
timestamp: 2026-03-24T00:00:00Z
---

# B-9: Compute PTDF matrix for TINY, verify dimensions and flow accuracy

## Result: PASS

## Approach

Used MATPOWER's native `makePTDF(baseMVA, bus, branch)` function to compute the DC PTDF matrix. Verified dimensions (46 branches x 39 buses) and validated flow predictions against DCPF reference solution from `rundcpf()`.

Checked for phase-shifting transformers by examining `mpc.branch(:, SHIFT)` -- case39 has **zero** phase-shifting transformers (all SHIFT values are zero). Therefore, no Pbusinj/Pfinj corrections were needed, though the corrected formula was tested as well for completeness.

Flow accuracy was verified using two methods:
1. **Uncorrected**: `flow = H * (Pbus/baseMVA) * baseMVA` (direct PTDF multiplication)
2. **Corrected**: `flow = (H * (Pbus/baseMVA - Pbusinj) + Pfinj) * baseMVA` (full correction with `makeBdc` outputs)

Both methods produce identical results since there are no phase shifters.

## Output

| Metric | Value |
|--------|-------|
| PTDF dimensions | 46 x 39 (branches x buses) |
| PTDF density | 71.91% |
| PTDF computation time | 0.0016 s |
| Max absolute error (uncorrected) | 1.478e-12 MW |
| Max absolute error (corrected) | 1.478e-12 MW |
| Mean absolute error (corrected) | 3.423e-13 MW |
| Phase-shifting transformers | 0 |

### Flow Comparison (top 5 branches by error)

All errors are at machine precision (~1e-12 MW). PTDF-predicted flows match DCPF flows to within numerical roundoff.

| Branch | From -> To | DCPF Flow (MW) | PTDF Flow (MW) | Error (MW) |
|--------|-----------|---------------|---------------|------------|
| 10 | 5 -> 6 | -514.754 | -514.754 | 1.478e-12 |
| 13 | 6 -> 11 | -338.202 | -338.202 | 1.251e-12 |
| 36 | 22 -> 23 | 41.224 | 41.224 | 9.948e-13 |
| 6 | 3 -> 4 | 54.115 | 54.115 | 8.882e-13 |
| 30 | 17 -> 18 | 200.685 | 200.685 | 8.527e-13 |

### Phase-Shifter Analysis

Case39 has no phase-shifting transformers (all `branch(:, SHIFT) == 0`). The standard formula `flow = PTDF * Pbus` is exact without corrections.

## Workarounds

None required. `makePTDF()` is a native MATPOWER function with a clean single-call API. The function accepts `baseMVA`, `bus`, and `branch` matrices directly and returns a dense PTDF matrix.

## Timing

- **Wall-clock:** 0.2853 s (including DCPF solve for reference)
- **PTDF computation only:** 0.0016 s
- **Timing source:** measured
- **Peak memory:** 1.8 MB
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/matpower/tests/extensibility/test_b9_ptdf_extraction.m`

Key API call:
```matlab
H = makePTDF(mpc.baseMVA, mpc.bus, mpc.branch);
% H is nl x nb (46 x 39), density 71.9%
% Predict flows: Pf = H * (Pbus / baseMVA) * baseMVA
```
