---
tag: doc-gaps
dimension: extensibility
test_id: B-6
observed: 2026-03-11
tool: powermodels
version: 0.21.5
---

# Doc Gap: Formulation-specific constraint methods lack docstrings

## Observation

The template-method split in `core/constraint_template.jl` + `form/*.jl` is the primary extension
point for writing new formulations. However, the formulation-specific implementations in
`form/dcp.jl`, `form/acp.jl`, etc. have no docstrings on most methods.

A developer extending PowerModels by writing new formulation-specific constraint implementations
(the recommended approach per official documentation) must:
1. Read `constraint_template.jl` to understand the template's parameter contract
2. Read an existing formulation file (e.g., `form/dcp.jl`) to infer the expected method signature
3. Read `core/base.jl` to understand `@pm_fields` and accessor function behavior

None of these steps are documented in docstrings. The official quickguide covers the high-level
pattern but does not provide a worked example of writing a new formulation-specific constraint
method. The PowerModels academic paper (Coffrin et al., 2018) provides the conceptual framework
but predates the current API.

## Affected Source Files

- `/opt/julia-depot/packages/PowerModels/VCmhH/src/form/dcp.jl` — 0 docstrings on constraint methods
- `/opt/julia-depot/packages/PowerModels/VCmhH/src/form/acp.jl` — sparse docstrings
- `/opt/julia-depot/packages/PowerModels/VCmhH/src/prob/opf.jl` — `build_opf` has empty docstring (`""`)
- `@pm_fields` macro — no docstring; behavior documented only via inline comment referencing `_IM.@def`

## Implication for Accessibility Grade

This is primarily an accessibility and learning-curve issue, not an extensibility limitation.
Developers familiar with Julia multiple dispatch and who read the source code can understand the
pattern quickly. However, the absence of docstrings increases the onboarding cost for power systems
engineers without strong Julia backgrounds.
