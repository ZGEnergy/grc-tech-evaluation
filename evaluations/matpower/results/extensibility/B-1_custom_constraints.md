---
test_id: B-1
tool: matpower
dimension: extensibility
network: TINY
protocol_version: "v10"
skill_version: "v1"
test_hash: "fececf15"
status: qualified_pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 0.2025
timing_source: measured
peak_memory_mb: 1.9
convergence_residual: null
convergence_iterations: null
loc: 283
solver: "GLPK"
timestamp: 2026-03-13T00:00:00Z
---

# B-1: Add flow gate limit to DC OPF and extract dual values

## Result: QUALIFIED PASS

## Approach

Used MATPOWER's documented `mpc.A`, `mpc.l`, `mpc.u` user constraint mechanism to add a linear constraint to DC OPF. The constraint limits the combined output of two generators (Gen 1 at bus 30, hydro, and Gen 10 at bus 39, gas_CC).

For DC OPF, the optimization variables are `[Va(1..nb); Pg(1..ng)]`. The user constraint `A * x <= u` is constructed as a 1-row sparse matrix with entries at the Pg columns for the two constrained generators.

Two cases were tested:
1. **Non-binding**: Limit set at 150% of unconstrained combined dispatch (1770 MW). Dual values are zero.
2. **Binding**: Limit set at 90% of unconstrained combined dispatch (1062 MW). Dual value `mu_u.usr = 2912.10`, objective increased from $98,648 to $100,447.

Dual values are accessible at `results.lin.mu.l.usr` and `results.lin.mu.u.usr` after the OPF solve.

## Output

| Metric | Value |
|--------|-------|
| Baseline objective | $98,648.14 |
| Non-binding objective | $98,648.14 |
| Binding objective | $100,446.71 |
| Non-binding dual (mu_u.usr) | 0.000000 |
| Binding dual (mu_u.usr) | 2912.101346 |
| Constrained combined dispatch | 1062.02 MW (limit: 1062.02 MW) |
| Objective increase | $1,798.57 (+1.8%) |

### Dual Value Verification

- **Non-binding case**: Both `mu_l.usr` and `mu_u.usr` are zero, confirming the constraint is not active.
- **Binding case**: `mu_u.usr = 2912.10` (non-zero), confirming the upper bound is active. The constrained dispatch exactly equals the limit (1062.02 MW), and the objective increases by $1,799.

### LMP Impact

The binding constraint shifts LMPs significantly near the constrained generators:
- Bus 30 (hydro gen): $5.00 -> $34.12 (+$29.12)
- Bus 39 (gas_CC gen): $40.00 -> $69.12 (+$29.12)
- Bus 1: $38.82 -> $77.62 (+$38.80)
- Central buses (16, 19-24): unchanged at $40.00

## Workarounds

- **What:** Used linear costs (LP formulation) with GLPK solver, and removed the 70% branch derating from A-3.
- **Why:** MIPS (MATPOWER's built-in interior-point solver) produces numerical singularity errors when user constraints (`mpc.A`) are added, for both LP and QP problems. The singularity worsens with each iteration (rcond degrades from 1e-17 to 1e-35). This was also observed in A-9 (SCOPF). HiGHS (which handles QP) is not available in the Octave devcontainer. The 70% branch derating from A-3 leaves insufficient system headroom for additional user constraints.
- **Durability:** stable -- `mpc.A/l/u` is a documented public API mechanism (MATPOWER manual Section 7.3). The GLPK solver is a documented solver option. The limitation is solver-specific (MIPS), not API-specific. With HiGHS or a commercial solver, quadratic costs + user constraints would likely work.
- **Grade impact:** The API for custom constraints (`mpc.A/l/u` with dual extraction at `results.lin.mu.l.usr`/`results.lin.mu.u.usr`) is clean and documented. The MIPS solver limitation restricts the practical scope to LP problems in the Octave environment.

## Timing

- **Wall-clock:** 0.2025 s (all three solves)
- **Timing source:** measured
- **Peak memory:** 1.9 MB
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/matpower/tests/extensibility/test_b1_custom_constraints.m`

Key API calls:
- `mpc.A = sparse(1, nb+ng)` — define user constraint matrix
- `mpc.u = limit / baseMVA` — upper bound (per-unit)
- `mpc.l = -Inf` — no lower bound
- `results.lin.mu.l.usr` / `results.lin.mu.u.usr` — extract dual values
