---
test_id: D-2
tool: pypsa
dimension: accessibility
network: N/A
protocol_version: v11
skill_version: v2
test_hash: cf89565f
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: null
solver: null
timestamp: 2026-03-24T18:30:00Z
---

# D-2: Documentation Audit

## Result: INFORMATIONAL

## Finding

Of the 10 Suite A tests assessed, 5 are implementable from official PyPSA
documentation alone (docs.pypsa.org), 3 required source code reading or GitHub
issue searches, and 2 required trial-and-error discovery of undocumented behavior.

## Evidence

### Per-Test Documentation Assessment

| Test | Docs Only? | Gap Description |
|------|-----------|-----------------|
| A-1 (DCPF) | **Yes** | `n.lpf()` well-documented. API page and examples cover linear power flow. |
| A-2 (ACPF) | **Yes** | `n.pf()` documented with convergence return values (`converged`, `n_iter`, `error`). Transformer `b` field dual semantics are undocumented but do not block basic usage from docs. |
| A-3 (DCOPF) | **Partially** | `n.optimize()` documented for OPF. Bus-level LMPs (`n.buses_t.marginal_price`) auto-populated. However, branch shadow prices (`mu_upper`/`mu_lower`) are NOT populated after `optimize()` -- extraction requires linopy model constraint access (`n.model.constraints[name].dual`), which is not shown in PyPSA docs. [api-friction A-3](../observations/api-friction-expressiveness-A-3_dcopf.md) |
| A-4 (AC Feasibility) | **No** | Chaining DC OPF dispatch into AC PF requires understanding the transformer `b` field convention mismatch. The shared loader's DC susceptance patch must be removed for AC analysis. Not documented anywhere. [unit-mismatch A-4](../observations/unit-mismatch-expressiveness-A-4_ac_feasibility.md) |
| A-5 (SCUC) | **Yes** | `committable=True`, `min_up_time`, `min_down_time`, `start_up_cost`, `shut_down_cost` are documented generator attributes. UC formulation well-covered in docs under "Unit Commitment" section. |
| A-6 (SCED) | **Partially** | No `fix_commitment()` API exists. Two-stage UC-then-ED workflow requires manually constructing `p_min_pu`/`p_max_pu` time-varying bounds. Not shown in any documentation example. [api-friction A-6](../observations/api-friction-expressiveness-A-6_sced.md) |
| A-9 (SCOPF) | **Partially** | `n.optimize.optimize_security_constrained()` is documented. However, the limitation that only Line (not Transformer) contingencies are accepted is undocumented. Users discover this by error message only. [api-friction A-9](../observations/api-friction-expressiveness-A-9_scopf.md) |
| A-10 (Lossy DCOPF) | **Yes** | Loss factors and `marginal_cost_quadratic` are documented generator attributes. |
| A-11 (Distributed Slack) | **No** | `n.pf(distribute_slack=True)` is documented, but using it after DC OPF hits the same transformer `b` field mismatch as A-4. The loader incompatibility is not documented. [convergence-quality A-11](../observations/convergence-quality-expressiveness-A-11_distributed_slack_opf.md) |
| A-12 (Multi-period Storage) | **Yes** | `StorageUnit`, `cyclic_state_of_charge`, `max_hours`, `efficiency_store`/`efficiency_dispatch` well-documented. [api-friction A-12 (positive)](../observations/api-friction-expressiveness-A-12_multiperiod_dcopf_storage.md) |

### Documentation Source

Assessed against docs.pypsa.org (accessed 2026-03-24). The documentation covers:
- Installation and quickstart
- Core components (buses, generators, loads, lines, transformers, storage units)
- Optimization formulations (objective, energy balance, dispatch limits, capacity)
- Unit commitment, power flow, Security-Constrained LOPF
- Storage optimization, custom constraints, rolling-horizon

**Not prominently documented:** Shadow price extraction, PTDF matrix access,
SubNetwork-level computation methods, transformer `b` field semantics for DC vs AC.

### Summary Statistics

- **Completable from docs alone:** 5 of 10 (A-1, A-2, A-5, A-10, A-12)
- **Required source code / GitHub issues:** 3 of 10 (A-3, A-6, A-9)
- **Required trial-and-error / guessing:** 2 of 10 (A-4, A-11)

### Key Documentation Gaps

1. **Shadow price assignment:** Branch constraint duals are not assigned to
   `n.lines_t.mu_upper`/`mu_lower` after `optimize()`. Users must discover
   the linopy constraint access pattern independently. [doc-gaps B-6](../observations/doc-gaps-extensibility-B-6_code_architecture.md)

2. **Transformer `b` field semantics:** The dual meaning of the `b` attribute
   (shunt susceptance for AC, series susceptance for DC B-matrix) is undocumented.
   Causes silent AC PF divergence when using a DC-oriented loader.

3. **SCOPF transformer exclusion:** The `branch_outages` restriction to Line-only
   components is not mentioned in API docs or docstrings.

4. **Two-stage UC/ED workflow:** No example or guide shows how to fix a commitment
   schedule and re-solve as economic dispatch.

5. **PTDF bus ordering:** The convention that PTDF columns follow `sub_network.buses_o`
   order (not `n.buses.index`) is undocumented. [doc-gaps B-9](../observations/doc-gaps-extensibility-B-9_ptdf_extraction.md)

6. **Mixin architecture:** The 8-mixin class composition and SubNetwork-level
   methods (`calculate_PTDF`, `calculate_BODF`, `calculate_B_H`) are only
   discoverable through source code. [doc-gaps B-6](../observations/doc-gaps-extensibility-B-6_code_architecture.md)

## Implications

PyPSA's documentation is strong for standard workflows (power flow, OPF, UC,
storage) but has meaningful gaps for intermediate-to-advanced use cases. The 50%
docs-only implementability rate is adequate but not excellent. The undocumented
transformer `b` field semantics are the most impactful gap, as they cause silent
failures in AC analyses that chain with DC results. The shadow price and PTDF
gaps affect users who need to go beyond standard OPF results.
