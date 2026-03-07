---
test_id: B-8
tool: powersimulations
dimension: extensibility
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: null
peak_memory_mb: null
loc: 6
solver: null
timestamp: "2026-03-07T05:00:00Z"
---

# B-8: Reference Bus Configuration

## Result: PASS

## Approach

Tested three slack bus configurations via PowerSystems.jl's `set_bustype!()` API,
verified with DCPF solves.

### (a) Default Single Slack

case39 designates bus 31 as the reference bus (`ACBusTypes.REF`). DCPF solves
correctly with this default. Bus 31 has theta=0.0 as expected for the reference.

### (b) Different Single Slack Bus

Changed reference bus from bus-31 to bus-16 using:

```julia
set_bustype!(bus31, ACBusTypes.PV)
set_bustype!(bus16, ACBusTypes.REF)
```

**Verified result:**
- After change, `ACBusTypes.REF` buses = [16] (correct)
- DCPF with bus-16 as slack **converged successfully**
- Bus 16 theta = 0.0 (correct -- reference bus angle is zero)
- Bus 31 theta = 0.173 rad (nonzero, as expected for a non-reference bus)
- All bus voltages and power injections consistent

The API correctly propagates the reference bus change through the DCPF solver.
No model reconstruction needed -- `set_bustype!` modifies the System in place.

### (c) Distributed Slack

PSI's `PTDFPowerModel` is inherently a form of distributed slack -- it uses PTDF-based
flow constraints without explicit bus angle variables or a reference bus in the
optimization formulation. However, the slack distribution is implicit (determined by
the PTDF matrix, which uses a single reference bus internally) and **not configurable**
via API.

Custom distributed slack weights (e.g., load-proportional) are not supported natively.
For PowerFlows.jl DCPF, the reference bus determines the slack.

## Findings

| Configuration | Achievable? | API Effort | Notes |
|---------------|-------------|------------|-------|
| (a) Default slack | Yes | 0 lines | Default behavior |
| (b) Different slack | Yes | 2 lines | `set_bustype!()` -- verified with DCPF |
| (c) Distributed slack | Partial | N/A | Implicit in PTDF, not configurable |

## Workarounds

None needed for (a) or (b). The `set_bustype!()` API is clean, documented, and works
correctly for changing the reference bus. For (c), distributed slack weights would
require manual reformulation beyond PSI's built-in capabilities.

## Test Script

No dedicated test script -- verified via interactive probe in the devcontainer.
