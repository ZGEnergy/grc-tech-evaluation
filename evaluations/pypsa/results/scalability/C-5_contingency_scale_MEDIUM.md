---
test_id: C-5
tool: pypsa
dimension: scalability
network: MEDIUM
protocol_version: "v4"
status: qualified_pass
workaround_class: data_prep
wall_clock_seconds: 612.7
peak_memory_mb: 2461
loc: null
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# C-5: Contingency Sweep Scale Test (MEDIUM)

## Result: QUALIFIED PASS

## Approach

Ran N-M contingency sweep on the ACTIVSg 10k-bus network with graph distance
x=5 and simultaneous outages m=4. Used `n.graph()` for NetworkX graph access,
attempted `n.lpf_contingency()` for vectorized N-1 sweep (failed), fell back
to manual line disabling (x=1e10) for contingency analysis.

## Output

| Metric | Value |
|--------|-------|
| Status | qualified_pass |
| Wall-clock | 612.7 s |
| Peak memory | 2,461 MB |
| Chosen bus | 13303 (degree 20) |
| Nearby buses (x=5) | 255 |
| Candidate lines | 270 |
| N-1 cases completed | 9 of 270 |
| N-1 time | 583 s |
| N-2 cases | Skipped (timeout) |
| N-3/N-4 cases | Skipped (timeout) |
| Total cases evaluated | 9 |

## Analysis

1. **Graph API:** `n.graph()` provides direct NetworkX access. Scoping 255
   buses within graph distance 5 of the highest-degree bus (13303, degree 20)
   identified 270 candidate lines. This scoping step is fast (~1s).

2. **lpf_contingency failed:** `n.lpf_contingency()` raised
   `'DataFrame' object has no attribute 'to_frame'` on the 10k-bus network.
   This appears to be a PyPSA bug or compatibility issue with the network
   structure. Fell back to manual N-1 analysis.

3. **Manual N-1 is slow:** Each manual LPF call on 10k-bus takes ~65s
   (including topology re-determination). Only 9 of 270 N-1 cases completed
   within the 600s timeout. This is the fundamental scalability bottleneck.

4. **No model reconstruction:** Line disabling modifies reactance in-place
   (x=1e10) without rebuilding the network object. However, each LPF call
   triggers full B-matrix factorization.

5. **N-2+ impractical:** With 270 candidates and 65s per LPF, N-2 would
   require 36,315 cases x 65s = ~27 days. Only N-1 is practical at 10k scale
   without lpf_contingency vectorization.

## Workarounds

- lpf_contingency failed; fell back to manual N-1 sweep
- Set x=0.0001 on 3 transformers with zero reactance
- Only N-1 sweep partially completed within timeout

## Timing

- **Wall-clock:** 612.7 s
- **N-1 sweep:** 583 s (9 cases)
- **Per-case LPF:** ~65 s
- **Peak memory:** 2,461 MB

## Test Script

**Path:** `evaluations/pypsa/tests/scalability/test_c5_contingency_scale.py`
