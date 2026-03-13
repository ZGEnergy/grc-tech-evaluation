---
test_id: C-5
tool: pypsa
dimension: scalability
network: MEDIUM
protocol_version: "v9"
skill_version: v1
test_hash: 1eef8491
status: pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 788.7
timing_source: measured
peak_memory_mb: 4966.5
convergence_residual: null
convergence_iterations: null
loc: null
solver: null
timestamp: 2026-03-11T00:00:00Z
---

# C-5: N-1 Contingency Sweep Scale

## Result: PASS

## Approach

Loaded ACTIVSg10k (10,000 buses, 9,726 lines) and ran base DCPF. Computed BODF matrix on the
main sub-network (12,706 × 12,706) via `sub_network.calculate_BODF()`. Selected the
highest-degree bus (bus 13303, degree=20) as focal bus, performed BFS depth 2 to identify
33 in-scope buses and 100 scoped lines. Pruned 2 zero-flow lines to get 98 N-1 contingency
cases.

Applied BODF post-contingency flow formula: `p0_new = p0_base + BODF[:, i] * p0_base[i]`
for each outage branch. Counted violations vs. `s_nom` limits.

Note: `n.lpf_contingency()` is broken on Python 3.12+ (isinstance check fails). Using
`sub_network.calculate_BODF()` directly — same algorithm, documented public API.

## Output

| Metric | Value |
|--------|-------|
| Network | ACTIVSg10k — 10,000 buses, 9,726 lines |
| Focal bus | 13303 (degree = 20) |
| BFS depth | 2 |
| Buses in scope | 33 |
| Lines in scope (before pruning) | 100 |
| Zero-flow lines pruned | 2 |
| **N-1 contingencies run** | **98** |
| Pruning ratio | 2.0% |
| Sub-network branches | 12,706 |
| BODF shape | 12,706 × 10,000 |
| **BODF compute time** | **426.7 s** |
| **N-1 sweep time** | **231.2 s** |
| **Per-contingency average** | **2,359 ms** |
| **Total wall-clock** | **788.7 s** |
| **Peak memory** | **4,966.5 MB** |
| Contingencies with overloads | 93 / 98 |
| Max overloads in any contingency | 6,030 |

93 of 98 N-1 contingencies trigger at least one branch violation. The high count reflects
zero-rated lines set to 1 MVA via `overwrite_zero_s_nom=1.0` — those 2,462 lines appear
as severe violations under any flow redistribution. In a production use case these lines
would be left unconstrained.

## Workarounds

- **What:** Used `sub_network.calculate_BODF()` instead of `n.lpf_contingency()`
- **Why:** `n.lpf_contingency()` is broken on Python 3.12+ due to an `isinstance(pd.Index, Sequence)` type check failure in PyPSA 1.1.2
- **Durability:** stable — `calculate_BODF()` is documented public API on SubNetwork; same algorithm
- **Grade impact:** None for computation; high-level API `n.lpf_contingency()` is broken but workaround is clean

## Timing

- **Wall-clock:** 788.7 s total (20.1 s load + 426.7 s BODF + 231.2 s N-1 sweep)
- **Timing source:** measured
- **Peak memory:** 4,966.5 MB (dominated by 12,706 × 10,000 float64 BODF matrix ≈ 965 MB + overhead)
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/scalability/test_c5_contingency_sweep_scale.py`
