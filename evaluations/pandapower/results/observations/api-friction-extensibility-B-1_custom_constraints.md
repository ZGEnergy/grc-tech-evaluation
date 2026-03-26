---
tag: api-friction
source_dimension: extensibility
source_test: B-1
tool: pandapower
severity: high
timestamp: "2026-03-24T00:00:00Z"
---

# Observation: Custom constraint injection requires monkey-patching internal OPF pipeline

## Finding

pandapower does not expose the PYPOWER `userfcn` callback mechanism in its public API, and discards constraint dual values during result extraction. Adding a custom flow gate constraint requires replicating an internal function (`_optimal_powerflow`) and monkey-patching the module reference.

## Context

B-1 tests custom constraint injection into DC OPF. pandapower internally uses PYPOWER's `add_userfcn` for dcline constraints, proving the mechanism works, but does not expose it for user-defined constraints. The PYPOWER result dict containing `lin.mu` (constraint duals) is discarded during `_extract_results` / `_copy_results_ppci_to_ppc`, making dual extraction impossible without intercepting the result before pandapower processes it.

## Implications

This is a significant API gap for users needing custom constraint injection (e.g., flow gates, interface limits, security constraints). The workaround is fragile because it depends on the internal structure of `_optimal_powerflow`. This should be noted in the Accessibility audit (D-series) as a documentation/API friction finding, and in the Maturity audit as an architectural gap where internal capabilities are not surfaced to users.
