---
test_id: B-3
tool: pandapower
dimension: extensibility
network: MEDIUM
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 3.71
peak_memory_mb: null
loc: 164
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# B-3: Solve N-1 DCPF contingencies. Collect max line loading across all cases.

## Result: PASS

## Approach

1. Loaded ACTIVSg10k (~10,000 buses, 10,701 branches)
2. Solved base case DCPF
3. Selected 50 branches (evenly spaced across the network)
4. For each branch: disabled via `in_service = False`, solved DCPF, recorded max loading, re-enabled

No model reconstruction per contingency case. In-place branch switching via DataFrame attribute modification.

## Output

| Metric | Value |
|--------|-------|
| Total branches | 10,701 |
| Branches tested | 50 |
| Cases converged | 50 / 50 (100%) |
| Base case max loading | 77.02% |
| Max loading across all contingencies | 85.01% |
| Per-case avg time | 0.040 s |
| Solve loop time | 2.00 s |

Worst case: line 6206 (bus 40073 -- 40272) caused max loading of 85.01%.

Top 5 worst contingency cases (max loading %): 85.01, 78.55, 78.37, 77.05, 77.04.

## Workarounds

None required.

## Timing

- **Wall-clock:** 3.71 s (total including load)
- **Solve loop:** 2.00 s for 50 contingencies
- **Per case:** 0.040 s average
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/pandapower/tests/extensibility/test_b3_contingency_loop_medium.py`
