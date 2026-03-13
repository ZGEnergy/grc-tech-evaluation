---
tag: solver-issues
source_dimension: expressiveness
source_test: A-12
tool: powermodels
severity: high
timestamp: 2026-03-11T00:00:00Z
---

# Observation: Multi-Period Storage OPF Requires SCIP (MIQP) — HiGHS and Ipopt Both Fail

## Finding

`PowerModels.build_mn_opf_strg` introduces `ZeroOne` binary complementarity variables for storage charge/discharge exclusivity, making the problem a MIQP. HiGHS rejects it with `OTHER_ERROR`. Ipopt rejects `ZeroOne` constraints with `UnsupportedConstraint`. SCIP is required. This behavior is not prominently documented.

## Context

Test A-12 (24-hour multi-period OPF with BESS) used `instantiate_model(mn_data, DCPPowerModel, build_mn_opf_strg)`. Even though `DCPPowerModel` is a linear formulation, `build_mn_opf_strg` adds binary complementarity constraints (`variable_storage_indicator` → `ZeroOne`). HiGHS (LP/QP solver) fails at the MIQP. Ipopt (NLP solver) fails because it cannot handle integer variables. SCIP (MINLP) handles the problem and returns `OPTIMAL`.

## Implications

- **Scalability dimension (C-3, C-8):** SCIP is substantially slower than HiGHS for large networks. Multi-period storage OPF on SMALL/MEDIUM tiers may face prohibitive solve times or require relaxing the complementarity constraints.
- **Accessibility dimension:** The solver requirement is non-obvious. A user following standard PowerModels examples (which use HiGHS) would encounter a confusing failure on storage OPF with no guidance.
- **Extensibility dimension:** Any extension involving storage dispatch must account for MIQP solver requirements, limiting the choice of solvers and potentially requiring custom LP relaxations.
- **Workaround pattern:** Two-phase approach (SCIP for dispatch + HiGHS LP snapshots for LMPs) is needed for any storage OPF requiring dual variables.
