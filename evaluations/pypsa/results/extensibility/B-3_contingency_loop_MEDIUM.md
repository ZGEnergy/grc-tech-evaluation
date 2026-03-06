---
test_id: B-3
tool: pypsa
dimension: extensibility
network: MEDIUM
status: pass
workaround_class: null
wall_clock_seconds: 1422.7
peak_memory_mb: null
loc: 20
solver: null
timestamp: 2026-03-05T00:00:00Z
---

# B-3: N-1 Contingency Loop on MEDIUM (ACTIVSg10k), 100-branch subset

## Result: PASS

## Approach
Loop over first 100 lines in `n.lines.index`. For each: disable via `n.lines.loc[name, "active"] = False`, run `n.lpf()`, compute max loading, restore.

## Output
- 100 contingencies attempted, 96 succeeded, 4 failed (islanding)
- Per-contingency average: ~14.2s
- NaN max_loading values observed for some contingencies due to zero-impedance branches
- API method: toggle `active` flag, call `n.lpf()`, restore

## Workarounds
None needed for the contingency loop itself. Zero-impedance branches in ACTIVSg10k cause NaN in loading calculations but don't prevent the loop from running.

## Timing
- Wall-clock: 1422.7s (100 contingencies)
- Peak memory: null

## Test Script
Path: `evaluations/pypsa/tests/extensibility/test_b3_contingency_loop_medium.py`
