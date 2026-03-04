# Solver Configuration

Normalized solver settings for reproducible evaluation. All tools must use these
settings (or document why a deviation was necessary).

## Evaluation Solver Stack

All solvers are open-source. No commercial solvers (Gurobi, CPLEX) are used.

| Solver | Problem Types | Role |
|--------|--------------|------|
| HiGHS | LP, MILP, QP | Primary for linear/MILP problems |
| SCIP | LP, MILP | Secondary MILP solver |
| Ipopt | NLP | Primary for nonlinear (AC PF/OPF) |
| GLPK | LP, MILP | Lightweight baseline |

## Normalized Settings

### HiGHS (LP/MILP)

```
solver: highs
time_limit: 300          # 5 minutes per solve
mip_rel_gap: 0.01        # 1% MIP gap (matches A-5 pass condition)
presolve: on
threads: 1               # Single-threaded for reproducibility (record if parallelism used)
output_flag: true        # Enable solver output for diagnostics
```

For scalability tests (Suite C), also test with:

```
threads: <available_cores>   # Record actual core count
```

### SCIP (MILP)

```
solver: scip
limits/time: 300
limits/gap: 0.01
display/verblevel: 4
lp/threads: 1
```

### Ipopt (NLP)

```
solver: ipopt
max_iter: 10000
tol: 1e-6
acceptable_tol: 1e-4
print_level: 5
linear_solver: mumps      # Open-source linear solver
```

For convergence difficulties, try (per convergence-protocol.md):

```
warm_start_init_point: yes
mu_init: 1e-2
```

### GLPK (LP/MILP)

```
solver: glpk
tm_lim: 300000            # milliseconds
mip_gap: 0.01
msg_lev: GLP_MSG_ON
```

## Solver Selection per Test

| Test | Primary Solver | Secondary (if applicable) |
|------|---------------|--------------------------|
| A-1 (DCPF) | Direct (no optimizer) | — |
| A-2 (ACPF) | Ipopt | — |
| A-3 (DC OPF) | HiGHS | — |
| A-4 (AC Feasibility) | Ipopt | — |
| A-5 (SCUC) | HiGHS | SCIP |
| A-6 (SCED) | HiGHS | — |
| A-7 (Contingency) | Direct or HiGHS | — |
| A-8 (Stochastic) | HiGHS | — |
| C-3 (DC OPF scale) | HiGHS, GLPK | — |
| C-4 (SCUC scale) | HiGHS, SCIP | — |
| C-7 (Solver swap) | All available | — |

## Recording Requirements

For every test that uses a solver, record:
- Solver name and version
- Settings used (especially any deviations from defaults above)
- Termination status (optimal, feasible, infeasible, timeout, error)
- Solve time (wall-clock, not CPU time)
- Objective value (for optimization problems)
- Iteration count (for iterative solvers)

## Tool-Specific Solver Interface Notes

Document how each tool configures solvers:
- Is there a unified solver interface or per-solver configuration?
- Can solver settings be passed as a dictionary/kwargs?
- Does solver swap require reformulation or just a parameter change?
- Are solver-specific options accessible (not just generic time/gap)?

This information feeds into C-7 (Solver Swap) and the Extensibility assessment.
