---
test_id: D-2
tool: pypsa
dimension: accessibility
status: qualified_pass
timestamp: 2026-03-05
---

# D-2: Documentation audit -- can each Suite A test be done from docs alone?

## Finding

PyPSA's official documentation at docs.pypsa.org covers core functionality (DCPF, ACPF,
DC OPF) well, but has significant gaps around edge cases, import-path limitations, and
advanced features. 5 of 9 A-tests can be completed from docs alone; 4 require external
research or trial-and-error.

## Evidence

| A-test | Topic | From docs alone? | Notes |
|--------|-------|-------------------|-------|
| A-1 | DCPF | Yes | `n.lpf()` well documented. Import path friction not documented but discoverable. |
| A-2 | ACPF | Yes | `n.pf()` well documented with convergence options. |
| A-3 | DC OPF | Qualified | `n.optimize()` documented, but gencost import gap NOT documented. User must discover that `import_from_pypower_ppc` silently drops gencost and manually assign `marginal_cost` / `marginal_cost_quadratic`. |
| A-5 | SCUC | Qualified | UC attributes (committable, min_up_time, etc.) documented. However, MIQP limitation with HiGHS is NOT documented -- using quadratic costs with committable=True silently fails. User must discover they need linear costs only. |
| A-7 | Contingency sweep | No | No built-in N-M sweep function. Docs describe `n.graph()` and the `active` flag, but assembling a full contingency sweep (~120 LOC) requires substantial user effort. No example or tutorial for this workflow. |
| A-8 | Stochastic | Qualified | `n.set_scenarios()` documented for two-stage stochastic programming. However, incompatibility with pypower-imported networks is NOT documented. The feature crashes with a MultiIndex error on imported networks -- only works with networks built via `n.add()`. |
| A-9 | SCOPF | Qualified | `optimize_security_constrained()` exists and is documented, but the `branch_outages` parameter format is underdocumented. Users must experiment to determine it accepts a list of line index names. |
| A-10 | Lossy OPF | Yes | `transmission_losses` parameter in `n.optimize()` is documented with segment count. |
| A-11 | Distributed slack OPF | No | `distribute_slack` exists in `n.pf()` and is documented for power flow. However, docs do NOT clarify that this parameter is absent from `n.optimize()`. The `**kwargs` pass-through in optimize() silently ignores it. User cannot discover this limitation from docs. |

**Summary:**
- Fully documented (from docs alone): A-1, A-2, A-10 (3 of 9)
- Partially documented (requires discovery): A-3, A-5, A-8, A-9 (4 of 9)
- Not documented (must assemble from primitives or discover silently-missing features): A-7, A-11 (2 of 9)

## Implications

Core power flow and optimization are well-documented. The gaps cluster around: (1) silent
data loss in import paths, (2) solver-specific limitations not surfaced in docs, (3)
missing features that appear present due to `**kwargs` pass-through, and (4) advanced
workflows that require assembling primitives without guidance. The silent-failure patterns
(gencost drop, distribute_slack ignored, MIQP failure) are particularly problematic because
docs give no indication these issues exist.
