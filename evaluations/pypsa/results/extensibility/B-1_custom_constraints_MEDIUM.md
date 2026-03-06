---
test_id: B-1
tool: pypsa
dimension: extensibility
network: MEDIUM
status: pass
workaround_class: stable
wall_clock_seconds: 11.6
peak_memory_mb: null
loc: 6
solver: highs
timestamp: 2026-03-05T00:00:00Z
---

# B-1: Custom Constraints on MEDIUM (ACTIVSg10k)

## Result: PASS

## Approach
Two-phase workflow: `create_model()` -> access `model.variables["Line-s"]` -> `add_constraints()` -> `model.solve()` -> `assign_solution()`. Single-line flow gate constraint on highest-loaded line (L9187).

## Output
- Base objective: 1,254,138.74
- Constrained objective: 1,267,081.14 (increase of $12,942.40)
- Gate line: L9187 (base flow 1256.7 MW, s_nom 1256.7 MW)
- Gate threshold: 628.3 MW (50% of base flow)
- Constrained flow: 628.3 MW -- constraint respected
- 4 lines of constraint code (excluding model create/solve boilerplate)
- Solver status: optimal

## Workarounds
Zero-impedance transformers (x=0) must be fixed (set x=1e-4) to avoid SVD failure in `n.optimize()` post-processing. This is needed on MEDIUM (ACTIVSg10k) but not on TINY (case39).

## Timing
- Wall-clock: 11.6s (constrained solve only)
- Peak memory: null

## Test Script
Path: `evaluations/pypsa/tests/extensibility/test_b1_custom_constraints_medium.py`
