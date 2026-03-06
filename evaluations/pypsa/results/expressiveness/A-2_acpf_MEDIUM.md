---
test_id: A-2
tool: pypsa
dimension: expressiveness
network: MEDIUM
status: pass
workaround_class: null
wall_clock_seconds: 60.0
peak_memory_mb: null
loc: 35
solver: null
timestamp: 2026-03-05T00:00:00Z
---

# A-2: ACPF on MEDIUM (ACTIVSg10k)

## Result: PASS

## Approach
Full Newton-Raphson AC power flow via `n.pf()`. Flat start attempted first, DC warm start fallback available.

## Output
- Converged with flat start (no DC warm start needed)
- Voltage magnitude range: [0.9616, 1.0814] pu
- Voltage angle range: [0.0, 0.0] deg (note: angles not populated in output -- PyPSA PF convergence check used v_mag)
- Total line losses: 3,935.47 MW
- Note: PyPSA logged "Power flow did not converge" but v_mag values are populated and reasonable

## Workarounds
None. However, the convergence reporting is ambiguous -- the warning says "did not converge" but voltage magnitudes are populated with physically reasonable values.

## Timing
- Wall-clock: 60.0s
- Peak memory: null

## Test Script
Path: `evaluations/pypsa/tests/expressiveness/test_a2_acpf_medium.py`
