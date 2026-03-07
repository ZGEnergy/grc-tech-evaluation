---
test_id: B-3
tool: gridcal
dimension: extensibility
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 0.329
peak_memory_mb: null
loc: 155
solver: null
timestamp: 2026-03-06T02:00:00Z
---

# B-3: N-1 Contingency Loop

## Result: PASS

## Approach

Loaded the IEEE 39-bus network once. Ran N-1 DCPF contingencies for all 46 branches by toggling `branch.active = False`, solving DCPF via `vge.power_flow()`, then re-enabling with `branch.active = True`. No model re-parsing or cloning required.

## Output

### Baseline

- Converged: Yes
- Max flow: 830.0 MW
- Max loading: 76.67%

### N-1 Results

| Metric | Value |
|--------|-------|
| Total contingencies | 46 |
| Converged | 46 (100%) |
| Non-converged | 0 |
| Max loading across all cases | 160.42% |
| Worst contingency | Branch 26 ("21_22_1") |
| Wall-clock (loop only) | 0.212s |
| Per-contingency average | 4.6ms |

### Top 5 Most Loaded Contingencies

| Branch | Name | Max Loading (%) | Max Flow (MW) |
|--------|------|-----------------|---------------|
| 26 | 21_22_1 | 160.42 | 962.5 |
| 17 | 13_14_1 | 133.64 | 830.0 |
| 36 | 6_31_1 | 121.25 | 1455.0 |
| 22 | 16_21_1 | 114.75 | 830.0 |
| 28 | 23_24_1 | 114.75 | 962.5 |

### Model Integrity Verification

After completing the full N-1 loop, re-ran baseline DCPF. Max flow difference from original baseline: 0.0 MW. Model state fully restored -- no corruption from in-place branch toggling.

## API Quality

- `branch.active = False/True` -- clean in-place toggle, no model reconstruction
- `vge.power_flow()` re-solves with modified topology
- No need to clone or re-parse the model
- `ContingencyAnalysisDriver` exists as a built-in alternative for standard N-1 analysis
- The manual loop approach provides full control over result collection

## Timing

- **Baseline DCPF:** 0.118s
- **N-1 loop (46 cases):** 0.212s (4.6ms/case)
- **Total:** 0.329s

## Test Script

**Path:** `evaluations/gridcal/tests/extensibility/test_b3_contingency_loop.py`
