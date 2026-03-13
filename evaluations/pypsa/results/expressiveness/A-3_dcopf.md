---
test_id: A-3
tool: pypsa
dimension: expressiveness
network: TINY
protocol_version: v9
skill_version: v1
test_hash: 06c6eba9
status: qualified_pass
workaround_class: fragile
blocked_by: null
wall_clock_seconds: 1.400
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 209
solver: highs
timestamp: 2026-03-11T00:00:00Z
---

# A-3: DC OPF with gen costs and line flow limits (dcopf)

## Result: QUALIFIED PASS

## Approach

Loaded IEEE 39-bus network. Since `import_from_pypower_ppc` does not import gencost data, marginal costs were assigned manually: G0 = $10/MWh through G9 = $100/MWh (linear spread over 10 generators sorted by name). All branch flow limits derated 70% (`n.lines.s_nom *= 0.7`; same for transformers). DC OPF solved via `n.optimize(solver_name="highs")` with HiGHS LP settings.

LMPs extracted from `n.buses_t.marginal_price`. Shadow prices on binding line/transformer constraints extracted via `n.model.constraints` (linopy model) — `n.lines_t.mu_upper` is empty after `optimize()` in PyPSA v1.1.2.

## Output

**Solver:** HiGHS LP, 28 simplex iterations, optimal
**Objective value:** $370,208 /h

**LMPs ($/MWh):**

| Bus | LMP |    | Bus | LMP |
|-----|----|-----|-----|-----|
| 2   | 10.0 | | 3   | 763.3 |
| 30  | 10.0 | | 18  | 664.4 |
| 32  | 30.0 | | 4   | 653.1 |
| 33  | 40.0 | | 14  | 631.5 |

- LMP min: $10.00/MWh (buses 2, 30 — at cheap generators)
- LMP max: $763.27/MWh (bus 3)
- **LMP spread: $753.27/MWh**

**Optimal Dispatch (MW):**

| Generator | Dispatch |
|-----------|----------|
| G0 ($10) | 465.3 |
| G1 ($20) | 646.0 (at p_max) |
| G2 ($30) | 630.0 (at p_max) |
| G7 ($80) | 262.9 |
| G8 ($90) | 840.0 (at p_max) |
| G9 ($100) | 1100.0 (at p_max) |

**Binding Branch Constraints (shadow prices via n.model.constraints):**
- Lines: L2 (at upper limit), L21 (at lower limit) — 2 binding lines
- Transformers: T2, T6, T8, T10 — 4 binding transformers
- **Total: 6 binding branch constraints** (≥ 2 required)

## Workarounds

1. **What:** Manually assigned marginal costs `n.generators.at[name, "marginal_cost"] = cost`.
   - **Why:** `import_from_pypower_ppc` does not import gencost data (documented limitation).
   - **Durability:** stable — public API attribute assignment.
   - **Grade impact:** Low; this is a documented known limitation, not an expressiveness gap.

2. **What:** Shadow prices extracted from `n.model.constraints["Line-fix-s-upper"].dual` and `n.model.constraints["Line-fix-s-lower"].dual` (linopy model) rather than `n.lines_t.mu_upper`.
   - **Why:** `n.lines_t.mu_upper` and `mu_lower` are empty DataFrames after `n.optimize()` in PyPSA v1.1.2. The linopy model constraint names are internal naming conventions (`Line-fix-s-upper`, `Transformer-fix-s-lower`) not documented in the public API.
   - **Durability:** fragile — depends on internal constraint naming convention that could change without API deprecation notice.
   - **Grade impact:** B- to C+ range. Shadow prices ARE accessible but require reading source code to discover the constraint names.

## Timing

- **Wall-clock:** 1.400 s
- **Timing source:** measured
- **Solve time:** 0.339 s (HiGHS LP)
- **Peak memory:** not measured
- **CPU cores used:** 1 (configured)

## Test Script

**Path:** `evaluations/pypsa/tests/expressiveness/test_a3_dcopf_tiny.py`

Key API for shadow price extraction (workaround):
```python
# n.lines_t.mu_upper is empty — use model constraints instead
for cname in ["Line-fix-s-upper", "Line-fix-s-lower"]:
    dual_da = n.model.constraints[cname].dual
    nonzero_lines = dual_da.where(abs(dual_da) > 1e-6, drop=True)
```
