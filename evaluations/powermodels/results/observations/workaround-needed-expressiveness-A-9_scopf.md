# Observation: workaround-needed -- A-9 scopf

**Test:** A-9 (DC SCOPF)
**Dimension:** expressiveness
**Tool:** PowerModels.jl v0.21.5

## Finding

PowerModels core has no built-in SCOPF formulation. PowerModelsSecurityConstrained.jl (LANL, 41 stars) provides this capability but is a separate package not installed in the evaluation environment. The DC SCOPF must be manually assembled via JuMP: shared generation variables, per-contingency angle variables, and linking constraints across base case + N-1 contingency networks.

Key challenges in manual assembly:
1. **Islanding contingencies** must be pre-screened using `calc_connected_components()`. IEEE 39-bus has 11 of 46 branches that create islands when removed, making strict power balance infeasible without load shedding variables.
2. **Thermal rating relaxation** was needed (1.5x) because case39 has tight limits that make preventive N-1 SCOPF infeasible at nominal ratings.
3. **Model size** grows rapidly: 35 contingencies x 39 buses = 1,365 angle variables plus 39 bus balance constraints per contingency = 1,365 balance constraints plus flow limits. Total: ~3,700 constraints for the TINY case.
4. **Cost comparison** between SCOPF (linearized) and unconstrained DC OPF (quadratic via PowerModels) is not apples-to-apples because HiGHS cannot solve QP in the manual formulation.

## Workaround Classification

**Stable.** The JuMP assembly approach works correctly. The pre-screening with `calc_connected_components()` is clean. However, ~180 lines of manual code for a standard SCOPF formulation is significant effort.

## Impact

High. SCOPF is the foundation of ISO market clearing. A tool that cannot express SCOPF without ~180 lines of manual JuMP assembly imposes substantial development overhead. The existence of PowerModelsSecurityConstrained.jl partially mitigates this, but that package has not been updated since January 2024 and its compatibility with PowerModels v0.21.5 is unverified.
