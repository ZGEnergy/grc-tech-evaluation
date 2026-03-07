---
test_id: P2-3
tool: powersimulations
dimension: p2_readiness
network: TINY
protocol_version: "v4"
status: informational
workaround_class: null
wall_clock_seconds: null
peak_memory_mb: null
loc: null
solver: "HiGHS, Ipopt"
timestamp: "2026-03-07T05:30:00Z"
---

# P2-3: Commitment Injection (SCUC → DCOPF → ACPF Pipeline)

## Result: INFORMATIONAL

## Finding

The SCUC → DCOPF → ACPF pipeline is **achievable but requires significant manual effort**
due to PSI's architecture separating optimization (PSI) from power flow (PowerFlows.jl)
and a known unit mismatch issue.

### Step-by-Step Capability Assessment

| Step | Capability | Effort | Notes |
|------|-----------|--------|-------|
| 1. Obtain SCUC schedule | Native | Low | `ThermalStandardUnitCommitment` formulation |
| 2. Extract commitment binary | Native | Low | `read_variables()` → `OnVariable__ThermalStandard` |
| 3. Lock commitments for ED | Native | Low | `FixValueFeedforward` or `SemiContinuousFeedforward` |
| 4. Solve DCOPF with fixed UC | Native | Low | `ThermalBasicDispatch` + `FixValueFeedforward` |
| 5. Transfer dispatch to ACPF | Problematic | High | Unit mismatch (see A-4 observation) |
| 6. Run AC PF feasibility | Native | Low | `solve_powerflow(ACPowerFlow(), sys)` |

### Key Friction Points

**Step 5 is the bottleneck.** PSI's `read_variables()` returns `ActivePowerVariable`
values in a different unit basis than PowerSystems.jl's component accessors
(`get_active_power_limits()`). Dispatch values from PSI are ~100x larger than Pmax
values from the System, making direct transfer to PowerFlows impossible without
understanding the internal unit convention.

This was documented in detail in observation
`api-friction-expressiveness-A-4_ac_feasibility.md`.

### Two-Stage Simulation (Native Alternative)

PSI's `SimulationSequence` provides a native two-stage UC→ED workflow:

```julia
problems = SimulationProblems(
    UC = DecisionModel(uc_template, sys; optimizer=scip_solver, horizon=Hour(24)),
    ED = DecisionModel(ed_template, sys; optimizer=highs_solver, horizon=Hour(1))
)
sequence = SimulationSequence(
    problems = problems,
    feedforwards = Dict(
        "ED" => [SemiContinuousFeedforward(
            component_type = ThermalStandard,
            source = OnVariable,
            affected_values = [ActivePowerVariable]
        )]
    )
)
sim = Simulation("UC-ED", steps=24, problems=problems, sequence=sequence)
```

This handles UC→ED cleanly but does **not** include an ACPF feasibility check step.

### Overall Assessment

The pipeline is feasible for UC→ED (native support via `SimulationSequence`). The
ED→ACPF transfer requires a workaround for the unit mismatch that is currently
**fragile** (depends on undocumented internal conventions). For Phase 2, resolving
the unit convention between PSI and PowerFlows would be a priority.
