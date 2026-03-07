---
test_id: B-3
tool: gridcal
dimension: extensibility
network: MEDIUM
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 13.476
peak_memory_mb: null
loc: 150
solver: Linear (DCPF)
timestamp: 2026-03-06T03:00:00Z
---

# B-3: N-1 Contingency Loop (MEDIUM)

## Result: PASS

## Approach

Ran 50 N-1 DCPF contingencies on the 10k-bus network. Selected the top 50 most-loaded branches from the baseline DCPF. Each contingency disables a branch in-place via `branch.active = False`, solves DCPF, and re-enables the branch. Model integrity verified by comparing post-loop baseline with original.

## Output

### Baseline DCPF

| Metric | Value |
|--------|-------|
| Buses | 10,000 |
| Branches | 12,706 |
| Max flow (MW) | 2,035.36 |
| Max loading (%) | 83.95 |
| Baseline solve time | 0.376s |

### N-1 Loop (50 Contingencies)

| Metric | Value |
|--------|-------|
| Total contingencies | 50 |
| Converged | 50 |
| Non-converged | 0 |
| Loop wall clock | 13.1s |
| Per-contingency avg | 262.0ms |
| Max loading (worst case) | 91.2% |
| Worst contingency | 80088_80090_1 |

### Top 5 Most Loaded Contingencies

| Branch | Max Loading (%) | Max Flow (MW) |
|--------|----------------|---------------|
| 80088_80090_1 | 91.20 | 2,035.42 |
| 60774_60775_1 | 88.80 | 2,049.69 |
| 25937_25938_1 | 88.38 | 2,174.19 |
| 25594_25597_1 | 87.18 | 2,035.66 |
| 25595_25597_1 | 87.18 | 2,035.66 |

### Model Integrity

- Post-loop DCPF converged: Yes
- Max flow difference from baseline: 0.0 MW
- Model unmodified: Yes

## API Quality

- `branch.active = False/True` toggle works in-place without re-parsing
- 262ms per DCPF solve on 10k-bus network
- No state corruption after 50 toggle cycles
- No workarounds needed

## Test Script

**Path:** `evaluations/gridcal/tests/extensibility/test_b3_contingency_loop_medium.py`
