---
test_id: B-1
tool: matpower
dimension: extensibility
network: TINY
protocol_version: "v11"
skill_version: "v2"
test_hash: "fececf15"
status: qualified_pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 0.7008
timing_source: measured
peak_memory_mb: 1.8
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 210
solver: "GLPK"
timestamp: 2026-03-24T00:00:00Z
---

# B-1: Add flow gate limit to DC OPF and extract dual values

## Result: QUALIFIED PASS

## Approach

Used MATPOWER's documented `mpc.A`, `mpc.l`, `mpc.u` user constraint mechanism to add a linear constraint limiting a generator's output in DC OPF. The constraint `A * x <= u` targets the Pg variable for Gen 1 (bus 30) in the DC OPF variable vector `[Va(1..nb); Pg(1..ng)]`.

Case39 has polynomial (quadratic) generator cost curves (MODEL=2). Since GLPK handles only LP problems, costs were linearized to 2-point piecewise linear (PWL) by evaluating the quadratic at Pmin and Pmax. This is a necessary concession because MIPS (the built-in QP solver) fails to converge when user constraints are present, and HiGHS is not available in the Octave devcontainer.

Two cases tested per v11 methodology:

1. **Non-binding**: Limit set at 150% of unconstrained dispatch (1144.26 MW). Dual value is zero, objective unchanged.
2. **Binding**: Limit set at 50% of unconstrained dispatch (381.42 MW). Dual value is 0.6 $/MW, objective increases by $228.85 (+0.48%).

Dual values are accessible at `results.lin.mu.l.usr` and `results.lin.mu.u.usr` after the OPF solve.

## Output

| Metric | Value |
|--------|-------|
| Baseline objective | $47,728.09 |
| Non-binding objective | $47,728.09 |
| Binding objective | $47,956.94 |
| Non-binding dual (mu_u.usr) | 0.000000e+00 |
| Binding dual (mu_u.usr) | 6.000000e-01 |
| Gen 1 unconstrained dispatch | 762.84 MW |
| Gen 1 constrained dispatch | 381.42 MW (limit: 381.42 MW) |
| Objective increase | $228.85 (+0.48%) |

### Dual Value Verification

- **Non-binding case**: `mu_u.usr = 0.0` (zero), confirming the constraint is not active. Objective is identical to baseline.
- **Binding case**: `mu_u.usr = 0.6` (non-zero), confirming the upper bound is active. The constrained dispatch exactly equals the limit (381.42 MW), and the objective increases by $228.85.

### LMP Impact

The binding constraint shifts LMPs at the constrained generator bus:
- Bus 30: $10.70 -> $11.30 (+$0.60)

## Workarounds

- **What:** Used GLPK solver (LP) with piecewise-linear cost curves instead of MIPS (QP) with native quadratic costs. Quadratic gencost was linearized to 2-point PWL.
- **Why:** MIPS (MATPOWER's built-in interior-point solver) fails to converge when user constraints (`mpc.A`) are added. HiGHS (which handles both LP and QP) is not available in the Octave devcontainer. [solver-specific: MIPS singularity with user constraints]
- **Durability:** stable -- `mpc.A/l/u` is a documented public API mechanism (MATPOWER manual Section 7.3). GLPK is a documented solver option. The PWL cost linearization is a standard MATPOWER cost format. The limitation is solver-specific (MIPS), not API-specific.
- **Grade impact:** The custom constraint API (`mpc.A/l/u` with dual extraction at `results.lin.mu.u.usr`) is clean and documented. The solver limitation restricts practical scope to LP formulations in the Octave environment, but the API itself is fully functional.

## Timing

- **Wall-clock:** 0.7008 s (all three solves: baseline + non-binding + binding)
- **Timing source:** measured
- **Peak memory:** 1.8 MB
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/matpower/tests/extensibility/test_b1_custom_constraints.m`

Key API calls:
```matlab
mpc.A = sparse(1, nb+ng);            % define user constraint matrix
mpc.A(1, nb+gen_idx) = baseMVA;      % coefficient for Pg (in per-unit)
mpc.u = limit_mw;                    % upper bound (MW)
mpc.l = -Inf;                        % no lower bound
results.lin.mu.l.usr                  % lower bound dual
results.lin.mu.u.usr                  % upper bound dual
```
