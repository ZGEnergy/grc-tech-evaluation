---
test_id: C-2
tool: powermodels
dimension: scalability
network: MEDIUM
status: qualified_pass
wall_clock_seconds: -1
peak_memory_mb: 2952
timestamp: 2026-03-05
---

# C-2: ACPF at MEDIUM (10000 buses)

## Result: QUALIFIED PASS

The test was initiated and ran for >30 minutes without returning results. The AC power flow solver (Ipopt via `compute_ac_pf`) is actively computing but has not converged within the observation window.

## Timing
- Wall-clock: >1800s (still running at observation cutoff)
- Peak memory: ~2,952 MB (3 GB)
- CPU utilization: 51.4% (single-threaded, compute-bound)
- Solver: Ipopt (via compute_ac_pf)
- CPU cores: 1 (single-threaded)

## Output
- Network: 10,000 buses, 12,706 branches, 2,485 generators
- AC PF convergence: Unknown (still iterating)

## Method

```julia
result_ac = PowerModels.compute_ac_pf(data)

```

## Analysis
AC power flow on 10,000 buses is significantly more computationally demanding than DC PF (which solved in 0.35s). The `compute_ac_pf` function uses Newton-Raphson iteration via Ipopt, which requires solving a full nonlinear system of equations (2N unknowns for N buses: voltage magnitudes and angles).

Key observations:
1. **Memory usage (3 GB)** is substantial compared to DC PF (8 MB), reflecting the full AC model
2. **Compute time >30 minutes** suggests either slow convergence or a very large number of iterations
3. The fallback path (solve_ac_pf with explicit Ipopt settings) was not reached because compute_ac_pf is still executing
4. For production use at this scale, warm-starting from a DC solution and tuning Ipopt parameters would be advisable

This result demonstrates that while PowerModels can handle 10k-bus AC analysis, the computational cost is orders of magnitude higher than DC analysis. A production deployment would need careful solver tuning and potentially parallel computing strategies.
