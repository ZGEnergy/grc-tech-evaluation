---
test_id: C-3
tool: pypsa
dimension: scalability
network: MEDIUM
protocol_version: v11
skill_version: v2
test_hash: 174687a1
status: pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 604.09
timing_source: measured
peak_memory_mb: 4412.13
cpu_threads_used: 1
cpu_threads_available: 32
loc: 224
solver: HiGHS 1.13.1, GLPK 5.0
timestamp: 2026-03-24T17:45:00Z
---

# C-3: DC OPF on MEDIUM with HiGHS and GLPK

## Result: PASS

## Approach

Loaded ACTIVSg10k (10,000 buses, 9,726 lines, 2,485 generators) via the shared
`matpower_loader.load_pypsa()` with `overwrite_zero_s_nom=99999.0`. The shared
loader imports gencost data: 1,136 generators received costs from the `.m` file
(range $0.00--$34.77/MWh), while 1,349 generators had zero marginal cost (no gencost
entry). Zero-cost generators are dispatched at minimum cost in the merit order.

Ran `n.optimize(solver_name=...)` with both HiGHS and GLPK. Single-threaded
(threads=1 for HiGHS, default for GLPK) per solver-config.md.

Note: The wall-clock times include linopy model construction overhead (LP file
writing ~1.5s, constraint/variable creation) in addition to the actual solver time.
HiGHS reports 6.22s solver runtime vs 307.6s total `n.optimize()` call. The gap is
linopy model building and shadow price extraction [tool-specific].

## Output

### HiGHS Results

| Metric | Value |
|--------|-------|
| Solver status | optimal |
| Objective | $1,306,775 |
| Total dispatch | 150,917 MW |
| Generators dispatched | 2,157 / 2,485 |
| LMP min | -$23.79/MWh |
| LMP max | $195.07/MWh |
| LMP mean | $19.54/MWh |
| LMPs uniform? | No (network is congested) |
| Max line loading | 100.0% |
| Binding lines | 2 |
| Max flow | 3,856 MW |
| Solve time (full n.optimize) | 307.59 s |
| HiGHS solver runtime | 6.22 s |
| Simplex iterations | 5,346 |
| Peak memory | 4,412.1 MB |

### GLPK Results

| Metric | Value |
|--------|-------|
| Solver status | optimal |
| Objective | $1,306,775 |
| Total dispatch | 150,917 MW |
| Generators dispatched | 2,157 / 2,485 |
| LMP min | -$23.79/MWh |
| LMP max | $195.07/MWh |
| LMP mean | $19.54/MWh |
| LMPs uniform? | No |
| Max line loading | 100.0% |
| Binding lines | 2 |
| Max flow | 3,856 MW |
| Solve time (full n.optimize) | 289.55 s |
| Peak memory | 4,410.0 MB |

### Cross-Solver Comparison

| Metric | HiGHS | GLPK | Agreement |
|--------|-------|------|-----------|
| Objective ($) | 1,306,775.115 | 1,306,775.115 | Match to $0.001 |
| Total dispatch (MW) | 150,916.88 | 150,916.88 | Match |
| LMP mean ($/MWh) | 19.536 | 19.536 | Match |
| n.optimize() time (s) | 307.6 | 289.5 | GLPK faster overall |
| HiGHS solver-only (s) | 6.22 | N/A | — |
| Binding lines | 2 | 2 | Match |

Both solvers produce identical solutions. The large gap between solver runtime (6.22s
for HiGHS) and total `n.optimize()` time (307.6s) is dominated by linopy's LP model
construction and file I/O — a tool-specific overhead that is independent of solver choice.

### Congestion Note

Unlike the cross-tool watchpoints prediction of uniform LMPs on ACTIVSg10k, this
DCOPF with gencost-based marginal costs shows non-uniform LMPs (range -$23.79 to
$195.07/MWh) with 2 binding lines at 100% loading. The congestion pattern depends
on cost structure: the synthetic uniform costs used in prior evaluations produce
uniform LMPs, while the heterogeneous gencost-derived costs create locational price
differentiation.

## Workarounds

- **What:** Generator marginal costs assigned from gencost via shared loader.
- **Why:** `import_from_pypower_ppc` does not import the MATPOWER gencost table.
- **Durability:** stable — uses documented `matpowercaseframes` CaseFrames API.
- **Grade impact:** Minimal — gencost import is a known MATPOWER bridge gap.

- **What:** `overwrite_zero_s_nom=99999.0` for zero-rated branches.
- **Why:** MATPOWER rateA=0 means "no thermal limit" but PyPSA interprets it as zero capacity.
- **Durability:** stable — documented `overwrite_zero_s_nom` parameter.
- **Grade impact:** None — standard practice for MATPOWER imports.

## Timing

- **HiGHS n.optimize():** 307.59 s (solver-only: 6.22 s)
- **GLPK n.optimize():** 289.55 s
- **Total wall-clock:** 604.09 s
- **Timing source:** measured
- **Peak memory:** 4,412.13 MB
- **CPU threads used:** 1
- **CPU threads available:** 32

## Test Script

**Path:** `evaluations/pypsa/tests/scalability/test_c3_dcopf_medium.py`
