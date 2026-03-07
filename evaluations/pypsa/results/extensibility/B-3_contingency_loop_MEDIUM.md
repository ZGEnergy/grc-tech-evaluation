---
test_id: B-3
tool: pypsa
dimension: extensibility
network: MEDIUM
protocol_version: "v4"
status: fail
workaround_class: null
wall_clock_seconds: null
peak_memory_mb: null
loc: null
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# B-3: N-1 contingency loop (MEDIUM -- ACTIVSg10k)

## Result: FAIL (impractical runtime)

## Details

The B-3 N-1 contingency loop on the 10,000-bus ACTIVSg10k network is impractical at MEDIUM
scale. The test iterates over all 12,706 branches (9,726 lines + 2,980 transformers), running
`n.copy()` + `n.lpf()` for each contingency.

**Performance observed:**
- After ~15 minutes, only ~41 contingency iterations completed (~1 iter/min)
- Estimated total runtime: ~200+ hours for full N-1 sweep
- Each iteration involves a deep copy of the 10k-bus network + LPF solve

**Root cause of slowness:**
1. `n.copy()` deep-copies the entire 10k-bus network each iteration (~expensive)
2. `n.lpf()` solves a 10k x 10k sparse system each time (~15s per solve)
3. The susceptance matrix is singular (zero-impedance branches), causing `MatrixRankWarning`
   and NaN flows on every iteration

**Alternative approaches not tested:**
- `n.lpf_contingency()` (vectorized N-1) -- has a known bug in PyPSA v1.1.2
- In-place modification without copy -- would avoid the deep-copy overhead
- Fixing zero-impedance branches first -- would eliminate the singular matrix issue

**Note:** The TINY (case39) test passed with 46 branches in ~0.5s. The 276x increase in
branch count, combined with the ~300x increase in per-LPF cost, makes the naive
copy-and-solve loop impractical at 10k-bus scale.
