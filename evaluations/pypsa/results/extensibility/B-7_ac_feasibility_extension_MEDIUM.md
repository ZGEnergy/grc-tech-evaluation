---
test_id: B-7
tool: pypsa
dimension: extensibility
network: MEDIUM
status: pass
workaround_class: stable
wall_clock_seconds: 537.2
peak_memory_mb: null
loc: 15
solver: highs
timestamp: 2026-03-05T00:00:00Z
---

# B-7: AC Feasibility Extension on MEDIUM (ACTIVSg10k)

## Result: PASS

## Approach
DC OPF -> fix generator p_set to dispatch -> run n.pf() for Newton-Raphson AC PF. All within same Network object.

## Output
- DC OPF: objective 1,254,138.74, dispatch 150,916.88 MW (497s)
- AC PF: converged with flat start (40s)
- Voltage range: [0.9616, 1.0814] pu
- 62 voltage violations (|v - 1.0| > 0.05)
- 0 thermal violations
- Same-model context: YES -- no export/reimport needed
- Workflow is natural pattern in PyPSA (not a workaround)

## Workarounds
Zero-impedance transformers (x=0) must be fixed to avoid SVD failure in `n.optimize()` post-processing. Same stable workaround as B-1/A-3 on MEDIUM.

## Timing
- Wall-clock: 537.2s (497s DCOPF + 40s ACPF)
- Peak memory: null

## Test Script
Path: `evaluations/pypsa/tests/extensibility/test_b7_ac_feasibility_extension_medium.py`
