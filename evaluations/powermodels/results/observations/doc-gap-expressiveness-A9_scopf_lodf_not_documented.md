---
tag: doc-gap
dimension: expressiveness
test_id: A-9
observed: 2026-03-11
tool: powermodels
version: 0.21.5
---

# Documentation Gap: LODF Computation and SCOPF API Pattern Not Documented

## Observation

PowerModels.jl provides `calc_basic_ptdf_matrix` for PTDF computation but has no corresponding `calc_basic_lodf_matrix` function and no documentation on:

1. How to compute LODF from PTDF
2. How to use PTDF/LODF in SCOPF via the two-level API
3. Which arc tuple direction to use when accessing `var(pm, :p)` in security constraints
4. That `make_basic_network` is required before `calc_basic_ptdf_matrix` (not documented in the function docstring)

## Impact

Implementing SCOPF requires reverse-engineering several undocumented patterns:

1. **LODF formula**: `LODF_lk = (PTDF[l,f_k] - PTDF[l,t_k]) / (1 - PTDF[k,f_k] + PTDF[k,t_k])` — not in any PowerModels doc, derived from power systems literature
2. **Branch flow variable access**: `var(pm, :p)[(br_idx, f_bus, t_bus)]` — the tuple key format is discoverable only by inspecting Julia internals or reading source code
3. **`make_basic_network` requirement**: `calc_basic_ptdf_matrix` silently requires pre-processed basic network (bus renumbering, no transformers, connected topology) — no error if called on raw data, just incorrect results

## Workaround

Implemented LODF from power systems literature. Used `typeof(PowerModels.var(pm, :p))` and `keys(PowerModels.var(pm, :p))` in a Julia REPL to discover the arc tuple structure at runtime.

## Comparison

Other tools (pandapower, GridCal) provide `calc_lodf_matrix` directly. PowerModels' lower-level design requires more power systems domain knowledge from the user to implement SCOPF. The `PowerModelsSecurityConstrained.jl` ecosystem package (not installed) likely abstracts this, but the core library leaves it to the user.
