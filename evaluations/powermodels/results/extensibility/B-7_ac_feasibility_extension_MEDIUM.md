---
test_id: B-7
tool: powermodels
dimension: extensibility
network: MEDIUM
status: fail
workaround_class: blocking
timestamp: 2026-03-12T00:00:00Z
protocol_version: "v9"
skill_version: v1
test_hash: 181fa512
failure_reason: no_viable_workaround_for_acpf_at_medium_scale
blocked_by: A-4_medium_acpf_failure
---

# B-7: AC Feasibility Extension — MEDIUM

## Result: FAIL

## Details

B-7 assesses the durability and effort level of the workaround used in A-4 (AC feasibility check). At MEDIUM scale, A-4 failed entirely — no ACPF workaround was viable.

**A-4 MEDIUM failure summary**:
- `compute_ac_pf` (NLsolve): Fails at ~1000-bus scale. Cannot reach 10k-bus.
- `solve_model(build_pf, Ipopt)`: MUMPS sparse direct solver runs out of memory at 10k-bus AC NLP. Ipopt exits with "Maximum CPU time exceeded" (300s CPU limit, 2093s wall clock) and MUMPS INFO(1) = -9 memory errors.

**Workaround assessment**:
- **Primary route** (`compute_ac_pf`): N/A — documented limitation, fails below MEDIUM scale
- **Fallback route** (Ipopt via `solve_model`): Fails due to MUMPS memory exhaustion at 10k-bus scale
- **Alternative routes not available**:
  - Iterative solver (BICGSTAB/GMRES via Krylov.jl): Would require implementing AC power flow from scratch — not a PowerModels extension
  - Pardiso/MA27/MA57 linear solvers: Not installed in evaluation environment; would require HSL license
  - Distributed slack relaxation: Not applicable to convergence failure

**Effort level**: N/A — no viable extension path exists without replacing the solver infrastructure

**Workaround classification: blocking** — AC power flow at MEDIUM scale is a hard ceiling with the current installation.

## Implications for Extensibility Dimension

This finding demonstrates that PowerModels.jl's AC power flow capability is bounded by NLsolve's Newton-Raphson solver at the low end (fails ~1000+ buses) and Ipopt+MUMPS DRAM limits at the high end (fails at 10k-bus MEDIUM scale). Users needing AC feasibility checks on transmission-scale networks (5000+ buses) must:
1. Use an external AC power flow tool (PowerFlow.jl, PowerSystems.jl + PowerSimulations.jl)
2. Obtain MA27/MA57/Pardiso license for MUMPS replacement
3. Use a distributed computing setup

None of these are achievable via PowerModels.jl's extension API — they require replacing core infrastructure.

## Workarounds

None viable at MEDIUM scale. Classification: **blocking**.

## Test Script

No separate test script — assessment based on A-4 MEDIUM run data.
`evaluations/powermodels/tests/expressiveness/test_a4_ac_feasibility_check_medium.jl`
