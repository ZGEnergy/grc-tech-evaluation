---
test_id: A-4
tool: matpower
dimension: expressiveness
network: TINY
protocol_version: "v10"
skill_version: "v1"
test_hash: "8531c61c"
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 0.1825
timing_source: measured
peak_memory_mb: 1.8
convergence_residual: null
convergence_iterations: null
loc: 242
solver: "MIPS (DC OPF), Newton-Raphson (ACPF)"
timestamp: 2026-03-13T00:00:00Z
---

# A-4: Take DC OPF dispatch from A-3, run full ACPF on that dispatch

## Result: PASS

## Approach

1. Loaded IEEE 39-bus case with differentiated costs and 70% branch derating (identical setup to A-3).
2. Solved DC OPF via `rundcopf(mpc, mpopt)` with MIPS solver to obtain dispatch.
3. **In the same model context** (no file export/reimport), transferred the DC OPF result struct directly as the starting point for AC PF: `mpc_ac = results_dc;`.
4. Reset voltage magnitudes to flat start (1.0 pu) and angles to 0.
5. Ran AC power flow via `runpf(mpc_ac, mpopt_ac)` with Newton-Raphson solver and Q-limit enforcement (`pf.enforce_q_lims = 1`).
6. Identified voltage violations, thermal violations, and reactive power limit violations from the results.

The entire workflow stays within the `mpc` struct — MATPOWER's data model supports direct modification and re-solving without any file I/O. The DC OPF result struct contains all fields needed for AC PF initialization.

## Output

| Metric | Value |
|--------|-------|
| DC OPF objective | $219,748.32 |
| DC OPF time | 0.1107 s |
| AC PF time | 0.0718 s |
| Total time | 0.1825 s |
| AC PF converged | Yes |

### Voltage Analysis

| Metric | Value |
|--------|-------|
| VM range | [0.9820, 1.0636] pu |
| Buses outside [Vmin, Vmax] | 1 (bus 36: VM=1.0636, limit 1.06) |
| Buses outside [0.95, 1.05] | 6 |

### Thermal Violations

| Branch | From-To | S (MVA) | RATE_A (MVA) | Loading |
|--------|---------|---------|-------------|---------|
| 20 | 10->32 | 661.78 | 630.00 | 105.0% |
| 37 | 22->35 | 663.46 | 630.00 | 105.3% |
| 46 | 29->38 | 840.35 | 840.00 | 100.0% |

3 thermal violations identified. These are branches that were binding in the DC OPF — the reactive power flows in the full AC model push apparent power above the MW-only DC limits.

### Reactive Power

No Q-limit violations. All generators operate within their reactive power limits.

### Losses

- Total generation: 6,297.85 MW
- Total load: 6,254.23 MW
- Losses: 43.62 MW (0.70%)

## Workarounds

None required. MATPOWER's `mpc` struct serves as both input and output, enabling seamless workflow from DC OPF to AC PF within the same model context. The DC OPF result struct is directly usable as AC PF input — no export/reimport needed.

## Timing

- **Wall-clock:** 0.1825 s (DC: 0.1107 s, AC: 0.0718 s)
- **Timing source:** measured
- **Peak memory:** 1.8 MB
- **Solver iterations:** N/A (Newton-Raphson internal)
- **Convergence residual:** N/A
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/matpower/tests/expressiveness/test_a4_ac_feasibility.m`
