---
test_id: A-9
tool: pypsa
dimension: expressiveness
network: SMALL
status: pass
workaround_class: null
wall_clock_seconds: 131.7
peak_memory_mb: null
loc: 45
solver: highs
timestamp: 2026-03-05T00:00:00Z
---

# A-9: SCOPF on SMALL (ACTIVSg2000)

## Result: PASS

## Approach
Native SCOPF via `n.optimize.optimize_security_constrained(branch_outages=..., solver_name="highs")`. 100 monitored lines as contingency set. Baseline DC OPF solved first for comparison.

## Output
- Base DC OPF cost: 859,978.19
- SCOPF cost: 862,892.59 (cost increase of 2,914.41)
- Solver status: optimal
- LMP range: [-4.56, 23.07]
- 651,907 rows in the LP (vs 10,707 for base DCOPF) -- significant model expansion
- Native SCOPF support confirmed

## Workarounds
None needed. `branch_outages` parameter only accepts line names (not transformer names), which is a known API limitation.

## Timing
- Wall-clock: 131.7s
- Peak memory: null

## Test Script
Path: `evaluations/pypsa/tests/expressiveness/test_a9_scopf_small.py`
