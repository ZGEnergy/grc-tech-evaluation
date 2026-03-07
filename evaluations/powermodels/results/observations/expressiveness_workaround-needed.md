---
tag: workaround-needed
dimension: expressiveness
tool: powermodels
tests: [A-5]
timestamp: "2026-03-06T00:00:00Z"
---

# Workaround Needed: No Built-in SCUC -- Entire Formulation Must Be User-Assembled

PowerModels.jl is a steady-state OPF tool with no unit commitment capability. Test A-5 (SCUC) required building the entire formulation from scratch in JuMP (~140 lines of manual constraint code), with PowerModels contributing only:

- MATPOWER file parsing (`parse_file`)
- Network data access (bus/gen/branch dictionaries)

All UC-specific features were manual: binary commitment variables, min up/down time constraints, startup/shutdown coupling, ramp rates, and reserve requirements. Even the DC power flow constraints had to be re-implemented manually because PowerModels' `build_mn_opf` creates a quadratic objective that becomes MIQP when combined with binary variables -- which HiGHS cannot solve.

**Workaround classification:** Stable. The JuMP-based approach is well-defined and repeatable, but it effectively means PowerModels provides no value-add for SCUC beyond data parsing. The recommended alternative is the separate `UnitCommitment.jl` package (ANL-CEEESA), which is not part of the PowerModels ecosystem.

**Lines of code comparison:** A-3 (DCOPF, built-in) required 124 LOC including boilerplate. A-5 (SCUC, manual) required 295 LOC -- 2.4x more code for fundamentally the same network with temporal coupling.
