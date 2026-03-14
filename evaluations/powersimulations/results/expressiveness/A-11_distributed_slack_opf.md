---
test_id: A-11
tool: powersimulations
dimension: expressiveness
network: TINY
protocol_version: "v10"
skill_version: "v1"
test_hash: "95a0e3ae"
status: fail
workaround_class: blocking
blocked_by: null
wall_clock_seconds: null
timing_source: measured
peak_memory_mb: 581.1
convergence_residual: null
convergence_iterations: null
loc: 156
solver: HiGHS
timestamp: "2026-03-14T00:00:00Z"
---

# A-11: Distributed Slack DC OPF

## Result: FAIL

## Approach

Investigated whether PowerSimulations.jl or PowerModels.jl provides a distributed slack
formulation for DC OPF, where the power balance reference is distributed across multiple
generators according to participation factors/weights rather than concentrated at a single
reference bus.

**Symbol search in PowerModels.jl:** No symbols containing "slack", "distributed", or
"participation" were found in the PowerModels namespace.

**Symbol search in PowerSimulations.jl:** Found 30+ slack-related symbols, all pertaining
to **feasibility slack variables** (penalty-based constraint relaxation), not distributed
power balance slack:
- `SystemBalanceSlackDown`, `SystemBalanceSlackUp` — system-level balance violation penalties
- `FlowActivePowerSlackLowerBound`, `FlowActivePowerSlackUpperBound` — branch flow relaxation
- `ReserveRequirementSlack` — reserve constraint relaxation
- `BALANCE_SLACK_COST`, `CONSTRAINT_VIOLATION_SLACK_COST` — penalty cost parameters

**Network formulations checked:**
- `DCPPowerModel` — fixes one bus's voltage angle to 0 (single-slack)
- `PTDFPowerModel` — constructs PTDF matrix relative to a single slack bus
- `CopperPlatePowerModel` — single-node aggregation (no network at all)

None of these support distributed slack. The `use_slacks` option in PTDFPowerModel adds
feasibility slack variables (soft constraints), not distributed power balance.

## Output

No numerical output — the capability does not exist in the tool.

**PSI slack-related symbols (feasibility, not distributed slack):**
- `SystemBalanceSlackDown/Up` — system balance violation slack
- `FlowActivePowerSlackLowerBound/UpperBound` — branch flow slack
- `RateofChangeConstraintSlackDown/Up` — ramp rate slack
- `InterfaceFlowSlackDown/Up` — interface flow slack
- `LowerBoundFeedForwardSlack`, `UpperBoundFeedForwardSlack` — feedforward slack

## Workarounds

- **What:** No workaround found within PSI's API.
- **Why:** The reference bus convention is fundamental to both DCPPowerModel (via the angle
  reference constraint) and PTDFPowerModel (via the PTDF matrix construction). Changing
  this would require modifying the mathematical formulation at the PowerModels level.
- **Durability:** blocking — A manual JuMP-level workaround is theoretically possible
  (remove the angle reference constraint, add a distributed power balance equation with
  participation factors), but this would bypass PSI's entire network formulation layer
  and effectively be a custom model.
- **Grade impact:** Distributed slack is not an API-accessible feature. The tool provides
  no mechanism to set participation weights or distribute the power balance reference.

## Timing

- **Wall-clock:** not applicable (capability investigation only)
- **Timing source:** measured (symbol search ~5s)
- **Peak memory:** 581.1 MB (Julia process with PSI loaded)
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/powersimulations/tests/expressiveness/test_a11_distributed_slack_opf.jl`

## Observations

- **doc-gaps:** The distinction between "feasibility slack" (PSI's `use_slacks`) and
  "distributed slack" (power balance distribution) is not documented anywhere. Users may
  conflate the `SystemBalanceSlackDown/Up` variables with a distributed slack formulation.
- **api-friction:** The `PTDFPowerModel` `use_slacks` option name is misleading — it has
  nothing to do with the slack bus concept in power systems terminology.
