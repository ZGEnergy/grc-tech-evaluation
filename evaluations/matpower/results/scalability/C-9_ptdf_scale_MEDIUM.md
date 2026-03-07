---
test_id: C-9
tool: matpower
dimension: scalability
network: MEDIUM
protocol_version: "v4"
status: pass
workaround_class: stable
wall_clock_seconds: 28.74
peak_memory_mb: 1016.5
loc: 75
timestamp: "2026-03-06T16:00:00Z"
---

# C-9: PTDF Scale (MEDIUM, ACTIVSg 10k)

## Result: PASS (stable workaround)

## Approach

Compute PTDF matrix via `makePTDF(mpc)` on ACTIVSg 10k. The MEDIUM network has non-consecutive bus numbering, requiring `ext2int()` conversion before `makePTDF` — this is documented in the function's help text and error message.

Also computed LODF matrix via `makeLODF(H, mpc)`.

## Output

| Metric | PTDF | LODF |
|--------|------|------|
| Dimensions | 12,706 x 10,000 | 12,706 x 12,706 |
| Elements | 127M | 161M |
| Non-zeros (>1e-10) | 87.2M | — |
| Density | 68.6% | — |
| **Computation time** | **28.74s** | — |
| Memory estimate | **1,017 MB** | — |

### PTDF Properties

- Storage: dense (not sparse — 68.6% density makes sparse inefficient)
- Slack column: all zeros (correct)
- Value range covers full [-1, 1] spectrum as expected for DC shift factors

## Workarounds

- **What:** `ext2int()` conversion required before `makePTDF` on non-consecutively numbered networks
- **Why:** `makePTDF` requires consecutive bus numbering (internal ordering)
- **Durability:** stable — `ext2int()` is a core MATPOWER function, documented in the function help text, and the error message explicitly tells the user what to do
- **Impact:** One extra line of code; no effect on grade

## Timing

- Case load + ext2int conversion: 1.33s
- PTDF computation: 28.74s
- Total: ~33s (including DCPF verification attempt)

## Notes

- PTDF on 10k buses is computationally expensive (29s, 1 GB memory) but feasible on Octave
- The dense PTDF matrix (1 GB) is the main memory bottleneck — applications needing per-branch sensitivity on larger networks should use selective PTDF computation
- `makePTDF` supports distributed slack weights as an optional argument
- LODF computation builds on PTDF and adds branch-to-branch sensitivities

## Test Script

`evaluations/matpower/tests/scalability/test_c9_ptdf_scale_medium.m`
