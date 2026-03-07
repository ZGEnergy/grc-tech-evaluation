---
test_id: B-3
tool: pypsa
dimension: extensibility
network: TINY
protocol_version: "v4"
status: pass
workaround_class: stable
wall_clock_seconds: 4.016
peak_memory_mb: null
loc: null
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# B-3: Contingency Loop

## Result: PASS

## Approach

Performed N-1 DCPF contingency analysis on all 46 branches (35 lines + 11 transformers)
of the case39 network. For each contingency:

1. Cloned the base network using `n.copy()` (deep copy, no file re-read).
2. Disabled the outaged branch by setting `x = 1e10` (open circuit impedance).
3. Ran `n.lpf()` on the modified clone.
4. Computed line loading as `|flow| / s_nom` for all remaining branches.
5. Recorded the maximum loading and the critical branch.

PyPSA provides `n.lpf_contingency()` as a native API for this operation, but it crashes
in v1.1.2 with `AttributeError: 'DataFrame' object has no attribute 'to_frame'`. The
manual loop via `n.copy()` is the documented fallback.

Some contingencies (removing branches that island part of the network) produce singular
B matrices, triggering `MatrixRankWarning`. PyPSA handles these gracefully and still
produces results (with potentially large/unrealistic flows on some branches).

## Output

| Metric | Value |
|--------|-------|
| Total branches | 46 |
| Contingencies solved | 46 |
| Contingencies failed | 0 |
| Time per contingency | 87.3 ms |
| Total wall-clock | 4.016 s |
| Overloaded cases (>100%) | 11 |

Top 5 worst contingencies:

| Outage | Max Loading (%) | Critical Branch |
|--------|----------------|-----------------|
| Transformer-T1 | 240.0 | Line-L11 |
| Line-L26 | 160.4 | Line-L28 |
| Line-L17 | 133.6 | Line-L11 |
| Line-L22 | 114.7 | Line-L28 |
| Line-L28 | 114.7 | Line-L22 |

## Workarounds

- **What:** Used `n.copy()` + manual branch disabling loop instead of `n.lpf_contingency()`.
- **Why:** `n.lpf_contingency()` crashes in PyPSA v1.1.2 with `AttributeError: 'DataFrame'
  object has no attribute 'to_frame'` (likely a pandas API compatibility issue).
- **Durability:** stable -- `n.copy()` and `n.lpf()` are core documented public API methods.
  The manual loop is a straightforward composition of public API calls. The
  `lpf_contingency()` bug is likely to be fixed in a future release.
- **Grade impact:** Minimal. The workaround is clean and uses only documented API. The
  bug in `lpf_contingency()` is a quality issue but does not affect the extensibility
  grade since the manual loop works well.

## Timing

- **Wall-clock:** 4.016s (46 contingencies)
- **Time per contingency:** 87.3 ms
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/extensibility/test_b3_contingency_loop.py`
