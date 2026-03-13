---
tag: arch-quality
dimension: extensibility
test_id: B-6
observed: 2026-03-11
tool: powermodels
version: 0.21.5
---

# Arch Quality: Four-layer dispatch architecture provides clean extensibility

## Observation

PowerModels.jl's architecture separates public API, model lifecycle, formulation build, and solver into four distinct layers. Julia multiple dispatch is the sole extension mechanism — no plugin registry, no callback hooks, no inheritance-based overrides.

The four layers:
1. **Public API** (`prob/opf.jl`) — one-line entry points delegate to `solve_model`
2. **Model lifecycle** (`core/base.jl`) — `solve_model` → `instantiate_model` → `optimize_model!`
3. **Formulation build** (`build_opf` + constraint templates + formulation methods) — data extraction decoupled from math via template/dispatch split
4. **Solver** (JuMP/MOI) — completely isolated; solver swap = optimizer argument change

The separation of concerns is enforced by the type system: constraint templates are defined over `AbstractPowerModel` and never reference formulation-specific types; formulation-specific implementations are dispatched by type from the template.

## Implication for Extensibility Grade

This architecture is highly extensible without fighting the tool. New formulations require only: define a subtype, implement dispatched constraint methods, write a `build_*` function. Verified in tests B-1 through B-5. The `instantiate_model` / `optimize_model!` two-level API (confirmed in B-1) gives direct JuMP model access for ad-hoc constraint injection. This is a genuine architectural strength relative to tools with monolithic solve pipelines.
