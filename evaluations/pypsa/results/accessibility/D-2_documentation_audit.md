---
test_id: D-2
tool: pypsa
dimension: accessibility
network: N/A
status: informational
workaround_class: null
timestamp: 2026-03-13T12:00:00Z
protocol_version: v10
skill_version: v1
test_hash: cf89565f
---

# D-2: Documentation Audit

## Summary

Of the 10 Suite A tests (A-1 through A-12, excluding removed A-7/A-8), 5 could be
completed from official PyPSA documentation alone, 3 required source code reading or
GitHub issue searches, and 2 required trial-and-error or guessing.

## Per-Test Documentation Assessment

| Test | Completable from Docs? | Gap Description |
|------|----------------------|-----------------|
| A-1 (DCPF) | Yes | `n.lpf()` is well-documented. The API page and examples cover basic linear power flow. |
| A-2 (ACPF) | Yes | `n.pf()` is documented with convergence return values. However, the transformer `b` field dual semantics (DC vs AC) are not documented (observation: api-friction A-2). Users would discover the loader issue by trial and error. |
| A-3 (DCOPF) | Partially | `n.optimize()` is documented for OPF. However, shadow price extraction requires knowledge that `mu_upper`/`mu_lower` are NOT populated on the network after solve; users must read linopy model constraints (observation: api-friction A-3). This is not documented. |
| A-4 (AC Feasibility) | No | Chaining DC OPF dispatch into AC PF requires understanding the transformer `b` field convention mismatch (observation: unit-mismatch A-4). The documentation does not explain that the shared loader's DC susceptance patch must be removed for AC analysis. |
| A-5 (SCUC) | Yes | `committable=True`, `min_up_time`, `min_down_time`, `start_up_cost`, `shut_down_cost` are documented generator attributes. The UC formulation is well-covered in the docs. |
| A-6 (SCED) | Partially | No `fix_commitment()` API exists (observation: api-friction A-6). The two-stage UC-then-ED workflow requires manually constructing `p_min_pu`/`p_max_pu` time-varying bounds, which is not shown in any documentation example. |
| A-9 (SCOPF) | Partially | `n.optimize.optimize_security_constrained()` is documented, but the limitation that only Line (not Transformer) contingencies are accepted is not documented (observation: api-friction A-9). Users discover this by error message. |
| A-10 (Lossy DCOPF) | Yes | Loss factors and `marginal_cost_quadratic` are documented generator attributes. |
| A-11 (Distributed Slack) | No | `n.pf(distribute_slack=True)` is documented, but using it after DC OPF hits the same transformer `b` mismatch as A-4 (observation: convergence-quality A-11). The loader incompatibility is not documented anywhere. |
| A-12 (Multi-period Storage) | Yes | `StorageUnit`, `cyclic_state_of_charge`, `max_hours`, `efficiency_store`/`efficiency_dispatch` are well-documented (observation: api-friction A-12 -- positive). |

## Summary Statistics

- **Completable from docs alone:** 5 of 10 (A-1, A-2, A-5, A-10, A-12)
- **Required source code / GitHub issues:** 3 of 10 (A-3, A-6, A-9)
- **Required trial-and-error / guessing:** 2 of 10 (A-4, A-11)

## Key Documentation Gaps

1. **Shadow price assignment:** The docs do not explain that branch constraint duals
   are not assigned to `n.lines_t.mu_upper`/`mu_lower` after `optimize()`. Users must
   discover the linopy model constraint access pattern independently.

2. **Transformer `b` field semantics:** The dual meaning of the `b` attribute
   (shunt susceptance for AC, series susceptance for DC B-matrix) is not documented.
   This causes silent AC PF divergence when using a DC-oriented loader.

3. **SCOPF transformer exclusion:** The restriction of `branch_outages` to Line-only
   components is not mentioned in the API documentation or docstring.

4. **Two-stage UC/ED workflow:** No example or guide shows how to fix a commitment
   schedule and re-solve as economic dispatch.

5. **Mixin architecture and SubNetwork API:** Advanced computational methods
   (`calculate_PTDF`, `calculate_BODF`, `calculate_B_H`) are only discoverable
   through source code reading (observation: doc-gaps B-6).

6. **PTDF bus ordering:** The convention that PTDF columns follow `sub_network.buses_o`
   order (not `n.buses.index`) is not documented (observation: doc-gaps B-9).
