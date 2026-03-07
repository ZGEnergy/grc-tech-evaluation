---
test_id: B-3
tool: pandapower
dimension: extensibility
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 0.94
peak_memory_mb: null
loc: 145
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# B-3: N-1 DCPF contingency loop with max line loading collection

## Result: PASS

## Approach

Full N-1 contingency screening on all 46 branches (35 lines + 11 transformers) of the IEEE 39-bus network. Each contingency was evaluated by:

1. Disabling the branch in-place: `net.line.at[idx, "in_service"] = False`
2. Solving DCPF: `pp.rundcpp(net)`
3. Collecting max line loading from `net.res_line["loading_percent"]`
4. Restoring the branch: `net.line.at[idx, "in_service"] = True`

No model reconstruction, re-parsing, or re-instantiation required. The base model is modified in-place via DataFrame attribute assignment, which is pandapower's documented approach for branch switching.

## Output

| Metric | Value |
|--------|-------|
| Total branches (N-1 cases) | 46 |
| Converged cases | 46 (100%) |
| Non-converged cases | 0 |
| Base case max loading | 76.7% |
| Worst-case max loading | 160.4% |
| Solve loop time | 0.307 s |
| Per-case average | 6.7 ms |

Top 5 worst contingencies by max loading:

| Branch | Type | From-To | Max Loading % | Max Flow MW |
|--------|------|---------|---------------|-------------|
| Line 26 | line | 20-21 | 160.4% | 962.5 |
| Line 17 | line | 12-13 | 133.6% | 777.3 |
| Line 22 | line | 15-20 | 114.8% | 688.5 |
| Line 28 | line | 22-23 | 114.7% | 962.5 |
| Line 16 | line | 9-12 | 113.7% | 694.4 |

The worst contingency (line 26, bus 20-21 outage) causes 160.4% loading, well above 100%, indicating a thermal violation under N-1 conditions.

## Workarounds

None required.

## Timing

- **Wall-clock:** 0.94 s (total including network loading)
- **Solve loop:** 0.307 s (46 contingency DCPF solves)
- **Per-case average:** 6.7 ms
- **Peak memory:** not measured
- **Model reconstruction required:** No

## Test Script

**Path:** `evaluations/pandapower/tests/extensibility/test_b3_contingency_loop.py`
