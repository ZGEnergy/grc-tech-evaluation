---
test_id: A-3
tool: pypsa
dimension: expressiveness
network: MEDIUM
protocol_version: v9
skill_version: v1
test_hash: 06c6eba9
status: qualified_pass
workaround_class: fragile
blocked_by: null
wall_clock_seconds: 290.51
timing_source: measured
peak_memory_mb: 4412.3
convergence_residual: null
convergence_iterations: null
loc: 274
solver: highs
timestamp: 2026-03-11T00:00:00Z
---

# A-3: DC OPF with gen costs and line flow limits (dcopf) — MEDIUM

## Result: QUALIFIED PASS

## Approach

Loaded ACTIVSg10k via CaseFrames → ppc → `import_from_pypower_ppc(ppc, overwrite_zero_s_nom=9999.0)`. The `overwrite_zero_s_nom=9999.0` (not 1.0) is required because ACTIVSg10k has 2,462 zero-rated lines that carry up to 1,840 MW in the base-case DCPF — setting them to 1 MVA makes the OPF infeasible. Setting them to 9,999 MVA makes them effectively unconstrained while real-rated lines still enforce limits.

Assigned differentiated marginal costs to all 2,485 generators (linspace $10–$100/MWh sorted by name). Ran DC OPF via `n.optimize(solver_name="highs")`. Extracted LMPs from `n.buses_t.marginal_price` and shadow prices from `n.model.constraints` (linopy internal API — fragile workaround).

## Output

**Solver:** HiGHS LP, 5,187 simplex iterations, optimal

**Solve time:** 289.0 s (model build 27 s + HiGHS solve 2.5 s + overhead ~260 s for linopy model construction)

**Objective value:** $6,691,367/h

**LMP Statistics:**

| Metric | Value |
|--------|-------|
| LMP min | -$431.65/MWh |
| LMP max | $1,454.38/MWh |
| LMP mean | $70.51/MWh |
| LMP spread | $1,886.03/MWh |
| Unique LMP values | 6,017 of 10,000 buses |

The large LMP spread ($1,886) and 6,017 unique values confirm the network is congested — binding lines create LMP differentiation across the 10k-bus grid. The note in cross-tool-watchpoints.md that ACTIVSg10k is "uncongested at 84-85%" applies to the **base case with default branch limits**; with differentiated costs and real branch ratings enforced, congestion does emerge.

**Dispatch:** 150,917 MW total generation = total load (balanced)

**Binding Branch Constraints:**

| Type | Count |
|------|-------|
| Lines (binding) | 9 |
| Transformers (binding) | 4 |
| **Total** | **13** |

Lines with >99% utilization by flow check: 12 lines

**Binding lines (sample):** L6939, L7055, L7174, L9498, L2156, L4464, L4629, L4890, L7990

**Lines treated as unconstrained (9,999 MVA):** 2,459 lines, 3 transformers (originally zero-rated in MATPOWER data)

## Workarounds

1. **What:** `overwrite_zero_s_nom=9999.0` instead of default (1.0 or None) to handle 2,462 zero-rated lines.
   - **Why:** ACTIVSg10k's zero-rated lines carry substantial real power flows (up to 1,840 MW in DCPF) — 1 MVA capacity makes OPF infeasible. 9,999 MVA makes them non-binding.
   - **Durability:** stable — `overwrite_zero_s_nom` is a documented public parameter.
   - **Grade impact:** Low; the workaround is expected for this dataset.

2. **What:** Marginal costs assigned manually via `n.generators.at[name, "marginal_cost"] = cost`.
   - **Why:** `import_from_pypower_ppc` does not import gencost data (documented limitation).
   - **Durability:** stable — public API attribute assignment.
   - **Grade impact:** Low; documented known limitation.

3. **What:** Shadow prices extracted from `n.model.constraints["Line-fix-s-upper"].dual` (linopy model internals).
   - **Why:** `n.lines_t.mu_upper` is empty after `n.optimize()` in PyPSA v1.1.2. Same issue as TINY.
   - **Durability:** fragile — depends on undocumented internal linopy constraint naming convention.
   - **Grade impact:** B- to C+ range. Shadow prices are accessible but require source code reading.

## Timing

- **Wall-clock:** 290.5 s (full test including load + OPF + extraction)
- **Load time:** 1.4 s
- **OPF solve time (n.optimize call):** 289.0 s
  - HiGHS solve: ~2.5 s (5,187 iterations)
  - linopy model construction: ~260 s (dominant cost)
  - Model writing to HiGHS: ~0.45 s
- **Timing source:** measured
- **Peak memory:** 4,412 MB (4.3 GB — model construction allocates significantly more than DCPF)
- **CPU cores used:** 1

**Scale note:** The 260-second model construction overhead in linopy is the dominant cost. HiGHS itself solves in 2.5 s. For large-scale repeated OPF runs, the linopy overhead would be the bottleneck.

## Test Script

**Path:** `evaluations/pypsa/tests/expressiveness/test_a3_dcopf_medium.py`
