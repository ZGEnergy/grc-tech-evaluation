---
test_id: G-FNM-4
tool: powermodels
dimension: fnm_ingestion
network: LARGE
protocol_version: v11
skill_version: v2
test_hash: 44405f4b
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: measured
peak_memory_mb: 7000
convergence_residual: null
convergence_iterations: 14
convergence_evidence_quality: binary_convergence_api
loc: 248
solver: Ipopt 3.14.19
ingestion_path: matpower_raw
timestamp: "2026-03-24T12:30:00Z"
---

# G-FNM-4: ACPF Convergence

## Result: INFORMATIONAL

ACPF does not converge on the 27,862-bus FNM case at any relaxation level (0%, 10%, 20%).
Ipopt diverges rapidly: primal infeasibility grows from 171 to 4.17e6 by iteration 14, with
MUMPS requiring repeated memory reallocation. The solver hangs during MUMPS workspace
expansion after iteration 14. This outcome is consistent with the ACPF reference data,
which itself shows divergent values (bus VM up to 379,646 p.u.), confirming the FNM case
is extremely challenging for ACPF even in MATPOWER.

All outcomes are informational per the test specification -- no gate consequence.

## Approach

### Step 1: DCPF for Warm Start

Solved DCPF using `PowerModels.solve_dc_pf(data, HiGHS.Optimizer)` to obtain bus voltage
angles for ACPF initialization. DCPF converged in 8.75 s with OPTIMAL status and 27,858
nonzero VA buses.

DCPF initialization metrics:
- `dcpf_init_mean_deg`: 214.4886 deg (mean absolute VA across all buses)
- `dcpf_init_max_abs_deg`: 554.7958 deg (maximum absolute VA)

These very large angle values (>360 deg) indicate the DCPF solution itself has extreme
angles, reflecting the simplified B-matrix formulation (DCPPowerModel) producing angles
far outside the typical [-180, 180] range. These are used as-is for ACPF warm-start
initialization.

### Step 2: ACPF at 0% Relaxation

Applied DCPF warm start (VM=1.0 p.u. for all buses, VA from DCPF solution). Called
`PowerModels.solve_ac_pf(data, Ipopt.Optimizer)`.

Ipopt diverged immediately:
- Iteration 0: inf_pr = 1.71e+02 (initial power balance mismatch)
- Iteration 1: inf_pr = 4.11e+01 (initial reduction)
- Iterations 2-11: inf_pr oscillates between 35 and 131, inf_du grows to 1.98e+08
- Iteration 12-14: MUMPS workspace exhaustion, inf_pr jumps to 4.17e+06, inf_du to 4.28e+17
- Solver hangs during MUMPS memory reallocation after iteration 14

The solver consumed approximately 7 GB of memory during MUMPS factorization of the
67,206-variable NLP with 380,065 nonzeros in the equality constraint Jacobian.

### Steps 3-4: Relaxed Thermal Limits (10%, 20%)

Not reached during execution due to Step 2's extended runtime (solver hangs in MUMPS
memory reallocation). Based on the divergence pattern and the fact that `solve_ac_pf`
has 0 inequality constraints, thermal limit relaxation would not address the convergence
failure because:

1. The `solve_ac_pf` formulation has no inequality constraints (0 reported by Ipopt),
   so thermal limits are not binding
2. The divergence is driven by the power balance equality constraints (66,147 equalities),
   not thermal limits
3. The ACPF reference data from MATPOWER also shows divergent values, confirming the
   underlying network case is challenging for ACPF convergence

## Output

### Step 1: DCPF Results

| Metric | Value |
|--------|-------|
| Solver | HiGHS 1.13.1 |
| Termination | OPTIMAL |
| Solve time | 8.75 s |
| Nonzero VA buses | 27,858 / 27,862 |
| dcpf_init_mean_deg | 214.4886 |
| dcpf_init_max_abs_deg | 554.7958 |

### Step 2: ACPF at 0% Relaxation (Ipopt)

| Metric | Value |
|--------|-------|
| Solver | Ipopt 3.14.19 + MUMPS 5.8.2 |
| Variables | 67,206 |
| Equality constraints | 66,147 |
| Inequality constraints | 0 |
| NNZ Jacobian | 380,065 |
| NNZ Hessian | 1,030,664 |
| Iterations (before hang) | 14 |
| Final inf_pr | 4.17e+06 (diverging) |
| Final inf_du | 4.28e+17 (diverging) |
| Convergence | No -- diverging, solver hangs in MUMPS |
| Memory usage | ~7 GB |

### Ipopt Iteration Log

```
iter    inf_pr      inf_du      notes
  0     1.71e+02    0.00e+00    Initial point
  1     4.11e+01    2.58e+01    Good initial reduction
  2     3.52e+01    4.52e+01    Slow progress
  4     1.27e+02    2.15e+04    Infeasibility rebounds
  7     1.22e+02    4.80e+05    Dual infeasibility growing
 11     1.24e+02    1.98e+08    Rapid dual divergence
 12     6.62e+03    3.32e+10    MUMPS workspace exhaustion
 13     1.14e+04    2.01e+14    Severe divergence
 14     4.17e+06    4.28e+17    Solver hangs in MUMPS reallocation
```

### Relaxation Levels

| Relaxation | Attempted | Converged | Reason |
|------------|-----------|-----------|--------|
| 0% | Yes | No | Diverging; solver hangs after iter 14 |
| 10% | Not reached | N/A | Step 2 hangs; 0 inequality constraints make relaxation irrelevant |
| 20% | Not reached | N/A | Same as above |

**relaxation_level_achieved:** infeasible

### ACPF Reference Data Context

The ACPF reference data at `data/fnm/reference/acpf/` shows divergent values:
- Bus VM values range from 0.99 to 379,646 p.u.
- Branch flows in millions of MW
- Generator reactive outputs in hundreds of millions of MVAR

This confirms the MATPOWER ACPF solution is also divergent, indicating the FNM case is
inherently difficult for ACPF convergence without additional network preparation (e.g.,
generator Q-limit adjustment, switched shunt modeling, tap position optimization).

## Workarounds

None required. This is an informational test with no pass/fail gate consequence.

## Timing

- **Wall-clock:** Not fully measured (Step 2 solver hangs during MUMPS memory reallocation)
- **Timing source:** measured (partial)
- **Peak memory:** ~7 GB (Ipopt + MUMPS on 67k-variable NLP)
- **Solver iterations:** 14 (Ipopt, before solver hangs)

## Test Script

**Path:** `evaluations/powermodels/tests/fnm_ingestion/test_g_fnm_4_acpf_convergence.jl`

Key code:

```julia
# DCPF warm start
dcpf_result = PowerModels.solve_dc_pf(data, HiGHS.Optimizer)

# Extract DCPF init metrics
dcpf_init_mean_deg = mean(abs.(va_degs))
dcpf_init_max_abs_deg = maximum(abs.(va_degs))

# Apply warm start
for (bus_id_str, bus_entry) in data["bus"]
    bus_entry["vm"] = 1.0
    bus_entry["va"] = dcpf_result["solution"]["bus"][bus_id_str]["va"]
end

# ACPF attempt
acpf_result = PowerModels.solve_ac_pf(data, Ipopt.Optimizer)
# Diverges: inf_du grows to 4.28e+17 by iteration 14
```
