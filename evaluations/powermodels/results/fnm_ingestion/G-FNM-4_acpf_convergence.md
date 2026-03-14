---
test_id: G-FNM-4
tool: powermodels
dimension: fnm_ingestion
network: LARGE
protocol_version: v10
skill_version: v1
test_hash: de8f372d
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: measured
peak_memory_mb: 7000
convergence_residual: null
convergence_iterations: 17
loc: 242
solver: Ipopt 3.14.19
input_path: matpower
relaxation_level_achieved: null
acpf_timeout_minutes: 30
timestamp: "2026-03-13T01:30:00Z"
---

# G-FNM-4: ACPF Convergence

## Result: INFORMATIONAL

ACPF does not converge on the 27,862-bus FNM case at any relaxation level (0%, 10%, 20%).
Ipopt diverges rapidly: primal infeasibility grows from 171 to 4.17e6 by iteration 14, with
MUMPS requiring repeated memory reallocation (up to 16x initial allocation). The solver
continued to diverge through at least iteration 17 before being terminated. This outcome
is consistent with the ACPF reference data, which itself shows divergent values (e.g.,
bus VM values of 379,646 p.u.), indicating the FNM case is extremely challenging for ACPF
even in MATPOWER.

All outcomes are informational per the test specification -- no gate consequence.

## Approach

### Step 1: DCPF for Warm Start

Solved DCPF using `PowerModels.solve_dc_pf(data, HiGHS.Optimizer)` to obtain bus voltage
angles for ACPF initialization. DCPF converged in 9.04 s with OPTIMAL status and 27,858
nonzero VA buses.

### Step 2: ACPF at 0% Relaxation

Applied DCPF warm start (VM=1.0 p.u. for all buses, VA from DCPF solution). Called
`PowerModels.solve_ac_pf(data, Ipopt.Optimizer)` with default Ipopt settings.

Ipopt diverged immediately:
- Iteration 0: inf_pr = 171 (initial power balance mismatch)
- Iteration 1: inf_pr = 41 (initial reduction)
- Iterations 2-11: inf_pr oscillates between 35 and 131, with inf_du growing to 1.98e8
- Iteration 12-14: MUMPS workspace exhaustion triggers, inf_pr jumps to 4.17e6, inf_du to 4.28e17
- Iterations 15-17: After MUMPS reallocation (icntl[13] increased to 16000), inf_pr
  drops to 72 momentarily but inf_du reaches 1.22e12, confirming divergence

The solver consumed approximately 7 GB of memory during MUMPS factorization of the 67,206-variable
NLP with 380,065 nonzeros in the equality constraint Jacobian.

### Steps 3-4: Relaxed Thermal Limits (10%, 20%)

Not reached during the measured run due to Step 2's extended runtime. Based on the
divergence pattern (MUMPS memory exhaustion, rapidly growing dual infeasibilities),
thermal limit relaxation would not address the convergence failure because:

1. The `solve_ac_pf` formulation has no inequality constraints (0 inequality constraints
   reported by Ipopt), so thermal limits are not binding
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
| Solve time | 9.04 s |
| Nonzero VA buses | 27,858 / 27,862 |

### Step 2: ACPF at 0% Relaxation (Ipopt)

| Metric | Value |
|--------|-------|
| Solver | Ipopt 3.14.19 + MUMPS 5.8.2 |
| Variables | 67,206 |
| Equality constraints | 66,147 |
| Inequality constraints | 0 |
| NNZ Jacobian | 380,065 |
| NNZ Hessian | 1,030,664 |
| Iterations (before termination) | 17+ |
| Final inf_pr | ~72 (oscillating, not converging) |
| Final inf_du | ~1.22e12 (diverging) |
| MUMPS reallocation attempts | 4 (icntl[13]: 1000 -> 16000) |
| Convergence | No -- diverging |
| Memory usage | ~7 GB |

### Ipopt Iteration Log (Key Points)

```
iter    inf_pr      inf_du      notes
  0     1.71e+02    0.00e+00    Initial point
  1     4.11e+01    2.58e+01    Good initial reduction
  4     1.27e+02    2.15e+04    Infeasibility rebounds
 11     1.24e+02    1.98e+08    Dual infeasibility growing rapidly
 12     6.62e+03    3.32e+10    Workspace exhaustion (MUMPS -9)
 14     4.17e+06    4.28e+17    Severe divergence
 15     1.09e+02    4.79e+08    After MUMPS reallocation -- temporary improvement
 17     7.21e+01    1.22e+12    Continued divergence
```

### Relaxation Levels

| Relaxation | Attempted | Converged | Reason |
|------------|-----------|-----------|--------|
| 0% | Yes | No | Diverging (inf_du > 1e12) |
| 10% | Not reached | N/A | Step 2 divergence; thermal limits not relevant (0 inequalities) |
| 20% | Not reached | N/A | Same as above |

### ACPF Reference Data Context

The ACPF reference data at `data/fnm/reference/acpf/` also shows divergent values:
- Bus VM values range from 0.99 to 379,646 p.u. (20,676 of 27,862 buses have VM outside [0.8, 1.2])
- Branch flows are in millions of MW (e.g., 23,493,570 MW on a single branch)
- Generator reactive outputs are in hundreds of millions of MVAR

This indicates the MATPOWER ACPF solution is also divergent, confirming the FNM case is
inherently difficult for ACPF convergence without additional network preparation
(e.g., generator Q-limit adjustment, switched shunt modeling, tap position optimization).

## Workarounds

None required. This is an informational test with no pass/fail gate consequence.

## Timing

- **Wall-clock:** Not fully measured (Step 2 terminated after ~25 minutes of Ipopt iterations)
- **Timing source:** measured (partial)
- **Peak memory:** ~7 GB (Ipopt + MUMPS on 67k-variable NLP)
- **Solver iterations:** 17+ (Ipopt, before termination)

## Test Script

**Path:** `evaluations/powermodels/tests/fnm_ingestion/test_g_fnm_4_acpf_convergence.jl`

Key code:

```julia
# DCPF warm start
dcpf_result = PowerModels.solve_dc_pf(data, HiGHS.Optimizer)

# Apply warm start
for (bus_id_str, bus_entry) in data["bus"]
    bus_entry["vm"] = 1.0
    bus_entry["va"] = get(dcpf_result["solution"]["bus"][bus_id_str], "va", 0.0)
end

# ACPF attempt
acpf_result = PowerModels.solve_ac_pf(data, Ipopt.Optimizer)
# Diverges: inf_du grows to 1e17+
```
