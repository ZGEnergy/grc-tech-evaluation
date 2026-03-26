---
test_id: C-1
tool: powersimulations
dimension: scalability
network: MEDIUM
protocol_version: "v11"
skill_version: "v2"
test_hash: "a3d2aa6b"
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 0.131
timing_source: measured
peak_memory_mb: 760.9
loc: 188
solver: PowerFlows.jl (built-in DCPF)
cpu_threads_used: 1
cpu_threads_available: 32
timestamp: "2026-03-24T00:00:00Z"
---

# C-1: DCPF on MEDIUM (ACTIVSg 10k)

## Result: PASS

## Approach

Ran DC power flow on the ACTIVSg 10000-bus network using `solve_powerflow(DCPowerFlow(), sys)`
from PowerFlows.jl v0.9.0. Measured wall-clock on the second invocation (JIT warm-up on the first).
Peak memory measured via `/proc/self/status` VmHWM.

## Output

| Metric | Value |
|--------|-------|
| Wall-clock (timed run) | 0.131 s |
| Wall-clock (JIT warm-up) | 4.86 s |
| Peak memory (RSS) | 761 MB |
| Buses solved | 10,000 |
| Branches solved | 12,706 |
| Generators | 2,485 |
| System load time | 20.04 s |

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

### Branch Flows

| Metric | Value |
|--------|-------|
| Min flow | -1,848 MW |
| Max flow | 1,747 MW |
| Non-zero flows | 11,990 of 12,706 |

## Workarounds

None required.

## Timing

- **Wall-clock (DCPF, timed):** 0.131 s (JIT cached, second invocation)
- **Wall-clock (JIT warm-up):** 4.86 s (first invocation includes JIT compilation)
- **System load time:** 20.04 s
- **Timing source:** measured
- **Peak memory:** 761 MB (Julia process RSS)
- **CPU threads used:** 1
- **CPU threads available:** 32

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

None -- DCPF scales cleanly to 10K buses with sub-second solve times.
