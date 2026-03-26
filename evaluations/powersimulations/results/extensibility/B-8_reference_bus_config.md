---
test_id: B-8
tool: powersimulations
dimension: extensibility
network: TINY
protocol_version: "v11"
skill_version: "v2"
test_hash: "dad5cf97"
status: pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 0.717
timing_source: measured
peak_memory_mb: 1279.6
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 226
solver: HiGHS
timestamp: "2026-03-24T00:00:00Z"
---

# B-8: Reference Bus Configuration (3 Slack Configs, Compare LMPs)

## Result: PASS

## Approach

Solved DCOPF on Modified Tiny (differentiated costs, 70% branch derating) with three
different reference bus configurations:

- **(a) Default:** Bus 31 (the MATPOWER default REF bus)
- **(b) Alternate:** Bus 30 (hydro generator, cheapest)
- **(c) Third:** Bus 35 (nuclear generator, mid-network)

Reference bus was changed via `set_bustype!(bus, ACBusTypes.REF)` on the PowerSystems.jl
`System` object before building the `DecisionModel`. The previous REF bus was first
changed to PV type.

**v11 note:** The pass condition acknowledges that LMP invariance is the correct expected
behavior for DCOPF with a single slack bus. The reference bus only fixes the angle datum,
not the optimization result. LMPs are determined by the KKT conditions of the constrained
optimization, which are independent of the angle reference.

**Distributed slack limitation:** DCPPowerModel (angle-based DC OPF) does not support
distributed slack. PowerNetworkMatrices.jl supports distributed slack for PTDF computation
(via `dist_slack` parameter), but this does not propagate to PSI's OPF formulation. Three
single-slack configurations were tested.

## Output

**LMP comparison across configurations:**

| Config | Ref Bus | LMP Min ($/MWh) | LMP Max ($/MWh) | LMP Spread | LMP Mean |
|--------|---------|-----------------|-----------------|------------|----------|
| (a) Default | 31 | 7.7564 | 290.114 | 282.3576 | 163.5025 |
| (b) Bus 30 | 30 | 7.7564 | 290.114 | 282.3576 | 163.5025 |
| (c) Bus 35 | 35 | 7.7564 | 290.114 | 282.3576 | 163.5025 |

**LMP invariance confirmed:** LMPs are identical across all three configurations to
within machine precision:

| Comparison | Max Difference |
|-----------|----------------|
| (a) vs (b) | 9.354e-11 $/MWh |
| (a) vs (c) | 2.557e-10 $/MWh |
| (b) vs (c) | 1.953e-10 $/MWh |

This is mathematically correct: in a well-formulated DCOPF, LMPs are determined by the
optimization problem's KKT conditions (cost curves + binding branch constraints), not by
the reference bus choice. The reference bus only sets the angle datum.

**Bus-level LMP samples (identical across all configs):**

| Bus | LMP ($/MWh) | Note |
|-----|-------------|------|
| bus-30 | 7.76 | Hydro gen (cheapest), congested export |
| bus-32 | 22.60 | Nuclear gen |
| bus-39 | 119.09 | Swing bus area |
| bus-3 | 290.11 | Most congested import |

## Workarounds

- **What:** Used three single-slack configurations instead of (a) default, (b) alternate
  single, (c) distributed slack. System reconstruction required per configuration.
- **Why:** DCPPowerModel does not support distributed slack. The angle reference is
  hardcoded to a single bus. Also, the System must be reconstructed to change the reference
  bus because the bus type is read during model construction. [tool-specific]
- **Durability:** stable -- the `set_bustype!` API is a documented PowerSystems.jl
  function. The limitation on distributed slack is architectural (DCPPowerModel uses
  voltage angle variables with a single fixed reference). Users wanting distributed
  slack must switch to PTDFPowerModel.
- **Grade impact:** The reference bus is fully configurable for single-slack mode via
  documented API. Distributed slack requires a different network model choice
  (PTDFPowerModel), not a parameter on DCPPowerModel. Model reconstruction per
  configuration adds overhead but is functionally correct.

## Timing

- **Config (a):** 0.482 s (includes first-run overhead after warm-up)
- **Config (b):** 0.111 s
- **Config (c):** 0.123 s
- **Total:** 0.717 s
- **Timing source:** measured
- **Peak memory:** 1279.6 MB

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
  [tool-specific]
- **api-friction:** Changing the reference bus requires full model reconstruction
  (System load + template setup + build + solve). For iterative reference bus studies,
  this means O(n) full rebuilds rather than a parameter change on an existing model.
  [tool-specific]
- **workaround-needed:** Distributed slack is not available in DCPPowerModel. Users
  wanting distributed slack behavior must switch to PTDFPowerModel with distributed
  slack weights via PowerNetworkMatrices.jl, which is a different formulation choice.
  [tool-specific]
