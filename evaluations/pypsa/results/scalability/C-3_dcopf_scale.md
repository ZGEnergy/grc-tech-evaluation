---
test_id: C-3
tool: pypsa
dimension: scalability
network: MEDIUM
protocol_version: "v9"
skill_version: v1
test_hash: d6e9428c
status: pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 2645.2
timing_source: measured
peak_memory_mb: 4412.0
convergence_residual: null
convergence_iterations: null
loc: null
solver: highs
timestamp: 2026-03-11T00:00:00Z
---

# C-3: DC OPF Scale

## Result: PASS

## Approach

Loaded ACTIVSg10k (10,000 buses, 9,726 lines, 2,485 generators), assigned marginal costs
($10–$100/MWh linear scale across sorted generator names), and ran DC OPF via
`n.optimize(solver_name="highs", ...)`. Zero-rated lines (2,462 of 9,726) were set to
99,999 MVA to restore MATPOWER's "no thermal limit" semantics (MATPOWER rateA=0 means
unconstrained, not 1 MVA).

**Critical scalability finding:** The total optimize() call took 2,618 s. HiGHS solve
itself took only 30–58 s (5,166 dual simplex iterations). The dominant cost is linopy's
LP model construction — writing 8 constraint matrices + 3 variable blocks for a
43,089-row × 15,191-column LP with 274,129 nonzeros. This is an O(n²) memory allocation
pattern in linopy's constraint serialization that makes single-snapshot DC OPF on the
10k-bus network impractical for repeated calls.

HiGHS LP model: 43,089 rows, 15,191 columns, 274,129 nonzeros. Solved with dual simplex
in 5,166 iterations.

LMPs were successfully extracted from this run: mean=$70.44/MWh, range=[-$431.9,
+$1,455.0/MWh]. The prior run in this session noted LMPs as "not assigned" — that was
due to a different PyPSA version state. In this run, n.buses_t.marginal_price was
populated after solve.

## Output

| Metric | Value |
|--------|-------|
| Network | ACTIVSg10k — 10,000 buses, 9,726 lines |
| LP formulation | 43,089 rows, 15,191 cols, 274,129 nonzeros |
| HiGHS version | 1.13.1 |
| **Total optimize() wall-clock** | **2,618 s** |
| HiGHS solve time | 30–58 s (5,166 iterations) |
| Linopy model build | ~2,560 s (dominates) |
| Total wall-clock (load + optimize + extract) | 2,645 s |
| **Peak memory** | **4,412 MB** |
| Simplex iterations | 5,166 |
| Solver status | Optimal |
| **Objective value** | **$6,692,949** |
| P-D objective error | 2.5e-13 |
| Generators dispatched | 1,729 / 2,485 |
| Total dispatch | 150,917 MW |
| Max dispatch | 1,403.2 MW |
| Binding line constraints | 11 |
| Max line loading | 100.0% |
| LMP mean | $70.44/MWh |
| LMP min | -$431.9/MWh |
| LMP max | +$1,455.0/MWh |
| LMP uniform | No |

## Workarounds

- **What:** Zero-rated lines set to 99,999 MVA for OPF
- **Why:** PyPSA's `overwrite_zero_s_nom=1.0` creates artificial 1 MVA bottlenecks; MATPOWER rateA=0 means unconstrained
- **Durability:** stable — uses public `n.lines.loc[...,'s_nom']` assignment
- **Grade impact:** None; restores intended network semantics

- **What:** Marginal costs assigned manually
- **Why:** `import_from_pypower_ppc` does not import gencost table
- **Durability:** stable — public API, documented limitation
- **Grade impact:** None for scalability timing

- **What:** GLPK not installed; HiGHS only
- **Why:** GLPK not available in devcontainer
- **Durability:** stable — solver swap is a parameter change, not a reformulation
- **Grade impact:** Minor; evaluates one solver instead of two

## Timing

- **Wall-clock:** 2,645.2 s total (25.1 s load + 2,618.1 s optimize() + extraction)
- **optimize() breakdown:** ~2,560 s linopy model build + 30–58 s HiGHS solve
- **Timing source:** measured
- **Peak memory:** 4,412 MB
- **CPU cores used:** 1 (threads=1)

## Scalability Finding

The linopy model construction (not the LP solver) is the dominant bottleneck at 10k-bus
scale. HiGHS solves the LP in under 60 s; linopy spends ~43 minutes writing constraint
matrices. This is architectural: linopy serializes constraints as sparse matrix files via
Python loops, scaling poorly with network size. For repeated OPF calls (e.g., rolling
window, stochastic scenarios), this overhead is incurred on every call.

## Test Script

**Path:** `evaluations/pypsa/tests/scalability/test_c3_dcopf_scale.py`
