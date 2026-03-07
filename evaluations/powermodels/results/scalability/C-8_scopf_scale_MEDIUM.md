---
test_id: C-8
tool: powermodels
dimension: scalability
network: MEDIUM
protocol_version: "v4"
status: fail
workaround_class: stable
wall_clock_seconds: null
peak_memory_mb: null
loc: null
solver: HiGHS
timestamp: "2026-03-07T00:00:00Z"
---

# C-8: SCOPF Scale (MEDIUM, ACTIVSg 10k-bus, 500 contingencies)

## Result: NOT ATTEMPTED (expected timeout)

## Rationale

SCOPF on ACTIVSg 10k-bus with 500 contingencies would create an enormous LP/NLP.
At TINY scale (39 buses, 46 branches, 46 contingencies), SCOPF required a workaround:
PowerModels' native `solve_scopf` is minimal and could not handle even TINY with full
N-1. The A-9 TINY SCOPF used an iterative approach with `solve_mn_opf` and contingency
filtering.

At MEDIUM scale with 500 contingencies:

- **Base problem:** DC OPF on 10k-bus has ~23,000 variables and ~35,000 constraints
- **Per contingency copy:** Each contingency adds a full 10k-bus DC power flow
  (~20,000 additional constraints)
- **Total with 500 contingencies:** ~10,000,000 constraints and ~11,500,000 variables
  in the multi-network formulation

This problem size exceeds what HiGHS can solve within 300s on a single thread.
Even the A-9 SMALL SCOPF (2000-bus, subset of contingencies) required iterative
contingency filtering and still ran for several minutes.

## What Would Work

An iterative SCOPF approach (solve base OPF, check contingencies, add violated
contingencies, re-solve) could produce useful results if:
1. Only a small fraction of contingencies are actually binding
2. The solver can handle the reduced multi-network in time
3. PTDF-based screening pre-filters contingencies

PowerModels' multi-network OPF (`solve_mn_opf`) provides the mechanism, but the
problem size at 10k x 500 contingencies is beyond practical limits with open-source
solvers and single-threaded operation.

## Test Script

Based on: `evaluations/powermodels/tests/expressiveness/test_a9_scopf.jl`
