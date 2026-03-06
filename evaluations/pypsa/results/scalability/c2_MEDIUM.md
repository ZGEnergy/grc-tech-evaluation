---
test_id: c2
tool: pypsa
dimension: scalability
network: MEDIUM
status: fail
wall_clock_seconds: 138.98
peak_memory_mb: 0.00
solver: null
timestamp: 2026-03-05T00:00:00Z
---

# C-2: ACPF on MEDIUM (ACTIVSg 10k)

## Result: FAIL

## Approach
Loaded the ACTIVSg 10k-bus network. Attempted AC power flow (`n.pf()`) with three strategies:

1. **Flat start (default)**: `n.pf()` -- did not converge (138.98s)
2. **DC warm start**: ran `n.lpf()` first, then `n.pf()` -- did not converge (159.25s)
3. **Relaxed tolerance (1e-3)**: `n.pf(x_tol=1e-3)` with DC warm start -- did not converge (192.92s)

All three attempts failed to converge. The network has zero-impedance transformers that cause a singular B matrix, preventing proper initialization and Newton-Raphson convergence.

## Output

| Metric | Value |
|--------|-------|
| Buses | 10,000 |
| Lines | 9,726 |
| Transformers | 2,980 |
| Generators | 2,485 |
| Flat start converged | False |
| Flat start wall-clock | 138.98s |
| DC warm start converged | False |
| DC warm start wall-clock | 159.25s |
| Relaxed tolerance converged | False |
| Relaxed tolerance wall-clock | 192.92s |

## Timing
- Flat start wall-clock: 138.98s
- DC warm start wall-clock: 159.25s
- Relaxed tolerance wall-clock: 192.92s
- Peak memory: ~0 MB (tracemalloc did not capture due to exception path)
- CPU cores: 1 (single-threaded)

## Notes
- The ACPF non-convergence is primarily due to zero-impedance branches in the ACTIVSg 10k case that make the admittance matrix singular. This is a known data quality issue with the MATPOWER case import.
- PyPSA's Newton-Raphson PF solver does not have robust handling of zero-impedance branches (it does not automatically merge or substitute small impedance values).
- The `pf()` method ran but returned non-convergence rather than raising an exception. The convergence check revealed 0 iterations completed and NaN error values.

## Test Script
Path: `evaluations/pypsa/tests/scalability/test_c2_acpf_scale.py`
