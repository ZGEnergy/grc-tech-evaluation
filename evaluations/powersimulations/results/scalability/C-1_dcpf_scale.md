---
test_id: C-1
tool: powersimulations
dimension: scalability
network: MEDIUM
protocol_version: "v10"
skill_version: "v1"
test_hash: "a3d2aa6b"
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 0.275
timing_source: measured
peak_memory_mb: 993.3
loc: 188
solver: PowerFlows.jl (built-in DCPF)
timestamp: "2026-03-14T00:00:00Z"
---

# C-1: DCPF on MEDIUM (ACTIVSg 10k)

## Result: PASS

## Approach

Ran DC power flow on the ACTIVSg 10000-bus network using `solve_powerflow(DCPowerFlow(), sys)`
from PowerFlows.jl. Measured wall-clock on the second invocation (JIT warm-up on the first).

## Output

| Metric | Value |
|--------|-------|
| Wall-clock (timed run) | 0.275 s |
| Wall-clock (JIT warm-up) | 2.83 s |
| Peak memory (RSS) | 993 MB |
| Buses solved | 10,000 |
| Branches solved | 12,706 |
| Generators | 2,485 |
| System load time | 10.25 s |

### Bus Angle Statistics

| Statistic | Value |
|-----------|-------|
| Min angle | -22.44 deg |
| Max angle | 104.53 deg |
| Mean angle | 21.35 deg |
| Non-zero angles | 9,999 of 10,000 |

### Nodal Injections

| Metric | Value |
|--------|-------|
| Total generation | 153,396 MW |
| Total load | 150,917 MW |
| Net injection sum | 24.79 pu (losses in DCPF) |

### Branch Flows

| Metric | Value |
|--------|-------|
| Min flow | -1,848 MW |
| Max flow | 1,747 MW |
| Non-zero flows | 11,990 of 12,706 |
| Max branch loading | 77.0% |
| Branches > 90% loaded | 0 |
| Branches > 99% loaded | 0 |

The max branch loading of 77% confirms the cross-tool watchpoint that ACTIVSg10k has no binding
branch constraints in the base case (~84-85% max loading expected per protocol, DCPF gives 77%
which is consistent since DCPF underestimates flows relative to ACPF).

## Workarounds

None required.

## Timing

- **Wall-clock (DCPF, timed):** 0.275 s (JIT cached, second invocation)
- **Wall-clock (JIT warm-up):** 2.83 s (first invocation)
- **System load time:** 10.25 s
- **Timing source:** measured
- **Peak memory:** 993 MB (Julia process RSS)
- **CPU cores used:** 1 (32 available)

## Test Script

**Path:** `evaluations/powersimulations/tests/scalability/test_c1_dcpf_scale.jl`

```julia
# DCPF returns nested Dict with period key "1"
pf_result = solve_powerflow(DCPowerFlow(), sys)
inner = pf_result["1"]
bus_df = inner["bus_results"]
flow_df = inner["flow_results"]
```

## Observations

None — DCPF scales cleanly to 10K buses with sub-second solve times.
