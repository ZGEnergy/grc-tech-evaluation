---
test_id: A-7
tool: pypsa
dimension: expressiveness
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

# A-7: N-M contingency sweep (MEDIUM -- ACTIVSg10k)

## Result: FAIL (impractical runtime)

## Details

The A-7 contingency sweep on the 10,000-bus ACTIVSg10k network is impractical at MEDIUM
scale. After ~15 minutes of execution, only ~40 N-1 contingency iterations had completed
out of a candidate set sized by graph-distance scoping.

**Performance bottleneck:** Each contingency iteration requires:
1. Modifying line impedance to disable the outaged branch
2. Running `n.lpf()` on the full 10k-bus network
3. Restoring the original impedance

Each LPF call on the 10k-bus network takes ~15s (with singular matrix warnings due to
zero-impedance branches), making even N-1 sweeps over hundreds of candidate lines
take hours.

**Additional issues:**
- The susceptance matrix B is singular (zero-impedance branches), causing all flows to
  be NaN. The contingency results would be meaningless even if the sweep completed.
- N-2 and N-3 combinatorial sweeps would compound the already impractical N-1 runtime.
- `n.lpf_contingency()` (the vectorized alternative) also fails on this network due to
  a known bug in PyPSA v1.1.2.

**Note:** The TINY (case39) test passed in ~1.5s with 46 branches. The scaling from 46 to
12,706 branches combined with the per-LPF overhead on a singular 10k-bus matrix makes this
test impractical without data preprocessing (fixing zero-impedance branches) and/or using
a vectorized contingency method.
