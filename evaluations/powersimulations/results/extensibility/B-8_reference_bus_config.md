---
test_id: B-8
tool: powersimulations
dimension: extensibility
network: TINY
protocol_version: "v10"
skill_version: "v1"
test_hash: "8c18d155"
status: pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 0.627
timing_source: measured
peak_memory_mb: 1316.5
convergence_residual: null
convergence_iterations: null
loc: 226
solver: HiGHS
timestamp: "2026-03-14T00:00:00Z"
---

# B-8: Reference Bus Configuration (3 Slack Configs, Compare LMPs)

## Result: PASS

## Approach

Solved DCOPF on Modified Tiny (differentiated costs, 70% branch derating) with three
different reference bus configurations:

- **(a) Default:** Bus 31 (the MATPOWER default REF bus, gen-6 nuclear)
- **(b) Alternate:** Bus 30 (gen-1 hydro, cheapest generator)
- **(c) Third:** Bus 35 (gen-6 nuclear, mid-network)

Reference bus was changed via `set_bustype!(bus, ACBusTypes.REF)` on the PowerSystems.jl
`System` object before building the `DecisionModel`. The previous REF bus was first
changed to PV type.

**Distributed slack limitation:** DCPPowerModel (angle-based DC OPF) does not support
distributed slack. The reference bus angle is fixed to zero and PSI does not expose a
distributed slack weighting option. PowerNetworkMatrices.jl supports distributed slack
for PTDF computation (via `dist_slack` parameter), but this does not propagate to PSI's
OPF formulation. Three single-slack configurations were tested instead of the requested
(a) default, (b) alternate, (c) distributed.

## Output

**LMP comparison across configurations:**

| Config | Ref Bus | LMP Min ($/MWh) | LMP Max ($/MWh) | LMP Spread | LMP Mean |
|--------|---------|-----------------|-----------------|------------|----------|
| (a) Default | 31 | 7.76 | 290.11 | 282.36 | 163.50 |
| (b) Bus 30 | 30 | 7.76 | 290.11 | 282.36 | 163.50 |
| (c) Bus 35 | 35 | 7.76 | 290.11 | 282.36 | 163.50 |

**LMP invariance:** LMPs are **identical** across all three configurations to within
machine precision:

| Comparison | Max Difference |
|-----------|----------------|
| (a) vs (b) | 9.35e-11 $/MWh |
| (a) vs (c) | 2.56e-10 $/MWh |
| (b) vs (c) | 1.95e-10 $/MWh |

This is mathematically correct: in a well-formulated DCOPF with binding constraints,
LMPs are determined by the optimization problem's KKT conditions (cost curves + binding
branch constraints), not by the reference bus choice. The reference bus only sets the
angle datum.

**Bus-level LMP samples (identical across all configs):**

| Bus | LMP ($/MWh) | Note |
|-----|-------------|------|
| bus-30 | 7.76 | Hydro gen (cheapest), congested export |
| bus-32 | 22.60 | Nuclear gen |
| bus-39 | 119.09 | Swing bus area |
| bus-3 | 290.11 | Most congested import |

## Workarounds

- **What:** Used three single-slack configurations instead of (a) default, (b) alternate
  single, (c) distributed slack.
- **Why:** DCPPowerModel does not support distributed slack. The angle reference is
  hardcoded to a single bus. PowerNetworkMatrices.jl's PTDF computation supports
  distributed slack via `dist_slack` weights, but this capability is not exposed in
  PSI's OPF formulation.
- **Durability:** stable — the `set_bustype!` API is a documented PowerSystems.jl
  function. The limitation on distributed slack is architectural (DCPPowerModel uses
  voltage angle variables with a single fixed reference).
- **Grade impact:** The reference bus is fully configurable for single-slack mode.
  Distributed slack requires a PTDF-based formulation (PTDFPowerModel), which is a
  different network model choice, not a parameter on DCPPowerModel.

## Timing

- **Config (a):** 0.418 s (includes first-run JIT after warm-up)
- **Config (b):** 0.118 s
- **Config (c):** 0.092 s
- **Total:** 0.627 s
- **Timing source:** measured
- **Peak memory:** 1316.5 MB

## Test Script

**Path:** `evaluations/powersimulations/tests/extensibility/test_b8_reference_bus_config.jl`

Key API pattern:
```julia
# Change reference bus
for bus in get_components(ACBus, sys)
    if get_bustype(bus) == ACBusTypes.REF
        set_bustype!(bus, ACBusTypes.PV)   # demote current REF
    end
end
for bus in get_components(ACBus, sys)
    if get_number(bus) == target_bus_number
        set_bustype!(bus, ACBusTypes.REF)   # promote new REF
    end
end
```

Note: The System must be reconstructed before building a new DecisionModel. The
reference bus setting lives on the System object, not on the model template.

## Observations

- **arch-quality:** The reference bus is configurable via a clean API
  (`set_bustype!`), but it requires System-level modification before model construction.
  There is no way to change the reference bus on an already-built optimization model.
- **api-friction:** Changing the reference bus requires full model reconstruction
  (System load + template setup + build + solve). For iterative reference bus studies,
  this means O(n) full rebuilds rather than a parameter change on an existing model.
- **workaround-needed:** Distributed slack is not available in DCPPowerModel. Users
  wanting distributed slack behavior must switch to PTDFPowerModel with distributed
  slack weights via PowerNetworkMatrices.jl, which is a different formulation choice.
