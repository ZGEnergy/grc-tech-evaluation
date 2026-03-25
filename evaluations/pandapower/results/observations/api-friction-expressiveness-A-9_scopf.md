---
tag: api-friction
source_dimension: expressiveness
source_test: A-9
tool: pandapower
severity: high
timestamp: "2026-03-24T00:00:00Z"
---

# Observation: PYPOWER userfcn callback system exists but is not exposed through pandapower's public API

## Finding

pandapower bundles PYPOWER which includes a functional `userfcn` callback system (`add_userfcn`, `run_userfcn`) capable of injecting custom linear constraints at the OPF `formulation` stage. The `opf_model.add_constraints()` method supports `l <= A * x <= u` constraints. However, pandapower's `rundcopp`/`runopp` wrapper functions do not expose any public API to register user-defined callbacks -- the ppc dict is constructed internally via `_pd2ppc()` and the userfcn mechanism is used only for internal purposes (e.g., DC line constraints).

## Context

During A-9 (SCOPF), the evaluator investigated whether pandapower's OPF could be extended with N-1 contingency constraints. The PYPOWER subsystem has all the necessary infrastructure (`add_userfcn` at the `formulation` stage, `opf_model.add_constraints` for linear constraints), but pandapower's wrapper layer does not provide a public entry point to use it. This forces users to either bypass pandapower's OPF entirely (blocking workaround) or monkey-patch internal functions (fragile workaround).

## Implications

This finding directly affects the Extensibility assessment (B-1: custom constraint injection). pandapower's PYPOWER backend theoretically supports custom constraints, but the public API does not expose this capability. The gap between internal capability and public API should be noted in the Accessibility audit (D-4) as well -- documentation does not describe any path for user-defined OPF constraints.
