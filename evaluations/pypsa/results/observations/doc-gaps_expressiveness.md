# Observation: doc-gaps (expressiveness)

## Source Tests
A-8, A-9, A-11

## Findings

### 1. set_scenarios() Compatibility Not Documented (A-8)
The `set_scenarios()` API documentation does not mention that it is incompatible with networks imported via `import_from_pypower_ppc()`. The feature works with natively-built networks but crashes on imported ones due to a MultiIndex bug in `find_bus_controls()`.

### 2. optimize_security_constrained() Input Format (A-9)
The `branch_outages` parameter type hint says `Sequence | pd.Index | pd.MultiIndex | None` but does not clarify:
- Whether transformer names should be included and how
- Whether tuples `("Line", name)` or plain strings are expected
- What happens when the N-1 problem is infeasible (no helpful error message)

Only plain line name strings worked in practice.

### 3. distribute_slack Scope Not Documented (A-11)
The `distribute_slack` parameter is documented for `n.pf()` but its absence from `n.optimize()` is not explicitly noted. The `**kwargs` in `n.optimize()` silently accepts any keyword argument, making it easy to mistakenly believe the parameter is supported.

### 4. MIQP Limitation Not Prominently Documented (A-5)
The inability of HiGHS to solve MIQP problems is not documented in PyPSA's UC/optimization documentation. Users setting `committable=True` with `marginal_cost_quadratic > 0` get silently wrong results.
