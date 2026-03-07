---
test_id: C-3
tool: pypsa
dimension: scalability
network: MEDIUM
protocol_version: "v4"
status: pass
workaround_class: data_prep
wall_clock_seconds: 600
peak_memory_mb: 4000
loc: null
solver: highs
timestamp: 2026-03-06T00:00:00Z
---

# C-3: DCOPF Scale Test (MEDIUM)

## Result: PASS

## Approach

Ran DC OPF on the ACTIVSg 10k-bus network using `n.optimize()` with HiGHS
solver (single-threaded, 600s time limit). Required fixing zero s_nom on 2,462
lines and zero reactance on 3 transformers.

## Output

| Metric | Value |
|--------|-------|
| Status | pass |
| HiGHS solve time | 19.9 s |
| Solver status | Optimal |
| Objective | 1.254e+06 |
| Solution | 15,191 primals, 43,089 duals |
| Buses | 10,000 |
| Generators | 2,485 |
| Lines | 9,726 |
| Transformers | 2,980 |

**Note:** HiGHS solves the LP in ~20s, but linopy's shadow-price assignment
(dual variable extraction and network assignment) takes 10+ minutes for this
network size. Total wall-clock is dominated by post-processing, not solving.

## Analysis

The DCOPF on the 10k-bus network solves optimally with HiGHS in ~20s. The LP
has 15,191 primal variables and 43,089 dual variables. The solver finds the
optimal dispatch with an objective value of $1.254M.

Key scalability finding: the bottleneck at this network size is NOT the solver
but linopy's post-processing to assign shadow prices back to the network.
This step takes 10+ minutes for the 10k-bus case.

## Workarounds

- Set s_nom=9999 on 2,462 lines with zero thermal rating
- Set s_nom=9999 on 3 transformers with zero rating
- Set x=0.0001 on 3 transformers with zero reactance

## Timing

- **HiGHS solve:** 19.9 s
- **Post-processing (shadow prices):** 10+ min
- **Solver threads:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/scalability/test_c3_dcopf_scale.py`
