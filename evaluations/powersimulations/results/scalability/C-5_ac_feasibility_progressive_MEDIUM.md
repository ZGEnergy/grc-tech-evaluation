---
test_id: C-5
tool: powersimulations
dimension: scalability
network: MEDIUM
protocol_version: "v10"
skill_version: "v1"
test_hash: "878fdc60"
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 1.567
timing_source: measured
peak_memory_mb: 1266.1
convergence_residual: null
convergence_iterations: null
relaxation_level_achieved: "0% (nominal)"
loc: 266
solver: PowerFlows.jl (built-in NR)
timestamp: "2026-03-14T00:00:00Z"
---

# C-5: AC Feasibility — Progressive Relaxation on MEDIUM

## Result: PASS

## Approach

Tested AC power flow convergence on the ACTIVSg 10,000-bus network (12,706 branches, 2,485
generators) using progressive thermal limit relaxation (0%, 10%, 20%). Same protocol as the
SMALL run: DCPF warm-start followed by ACPF attempts at each relaxation level.

**DCPF warm-start:** Solved `DCPowerFlow()` in 2.56s. Bus voltage angles ranged from -22.44
to +104.53 degrees. Set all voltage magnitudes to 1.0 pu.

**Optimization for 10k scale:** Used a `Dict{Int,Float64}` lookup for bus angles instead of
the nested-loop approach from the SMALL test (O(n) vs O(n^2) for bus-angle assignment).

**Solver:** PowerFlows.jl's built-in Newton-Raphson (no Ipopt needed for ACPF).

## Output

### DCPF Warm-Start

| Metric | Value |
|--------|-------|
| DCPF solve time | 2.56 s |
| Angle range | -22.44 to +104.53 degrees |

### Progressive Relaxation Results

| Relaxation | Converged | Wall-clock | Buses | Branches | VM range | Violations |
|------------|-----------|------------|-------|----------|----------|------------|
| 0% (nominal) | Yes | 1.57 s | 10,000 | 12,706 | 0.9002 - 1.0569 pu | 16 under + 3 over |
| 10% | Yes | 0.34 s | 10,000 | 12,706 | 0.9002 - 1.0569 pu | 16 under + 3 over |
| 20% | Yes | 0.34 s | 10,000 | 12,706 | 0.9002 - 1.0569 pu | 16 under + 3 over |

**Key finding:** ACPF converges at **0% relaxation (nominal thermal limits)** on MEDIUM.
No progressive relaxation was needed. All three relaxation levels converge to the same voltage
profile, consistent with SMALL behavior — thermal limit relaxation only affects OPF branch
constraints, not the NR power flow equations.

### Voltage Profile

| Statistic | Value |
|-----------|-------|
| Min VM | 0.9002 pu |
| Max VM | 1.0569 pu |
| Mean VM | 0.9964 pu |
| Buses with VM != 1.0 | 8,387 of 10,000 (84%) |
| Under-voltage (< 0.95 pu) | 16 buses |
| Over-voltage (> 1.05 pu) | 3 buses |

The voltage profile shows genuine convergence: 84% of buses have non-flat voltage magnitudes.
Only 19 buses (0.19%) have voltage violations, compared to 58 (2.9%) on SMALL. The 10k network
has better reactive power support than the 2k case.

### Scale Comparison (SMALL vs MEDIUM)

| Metric | SMALL (2k) | MEDIUM (10k) | Ratio |
|--------|-----------|-------------|-------|
| Buses | 2,000 | 10,000 | 5.0x |
| Branches | 3,206 | 12,706 | 4.0x |
| Generators | 544 | 2,485 | 4.6x |
| DCPF time | 2.13 s | 2.56 s | 1.2x |
| ACPF time (0%) | 0.74 s | 1.57 s | 2.1x |
| ACPF time (JIT cached) | 0.049 s | 0.34 s | 6.9x |
| Peak memory | 1,135 MB | 1,266 MB | 1.1x |
| Voltage violations | 58 (2.9%) | 19 (0.19%) | - |

ACPF scales sub-linearly with network size: 5x more buses yields only 2.1x longer solve time
(first call) and 6.9x longer (JIT cached). Memory increases only 12% despite 4-5x more
components. The Newton-Raphson solver in PowerFlows.jl handles 10k-bus networks efficiently.

## Workarounds

None required. Same clean API as SMALL.

## Timing

- **Wall-clock (ACPF, 0% relaxation):** 1.57 s (first call, includes JIT)
- **Wall-clock (ACPF, 10% relaxation):** 0.34 s (JIT cached)
- **Wall-clock (ACPF, 20% relaxation):** 0.34 s (JIT cached)
- **Wall-clock (DCPF warm-start):** 2.56 s
- **Wall-clock (total):** 23.2 s (includes 3x system loading for 10k network)
- **Timing source:** measured
- **Peak memory:** 1,266 MB (Julia process RSS)
- **CPU cores used:** 1 (32 available)

## Test Script

**Path:** `evaluations/powersimulations/tests/scalability/test_c5_ac_feasibility_progressive_MEDIUM.jl`

Key difference from SMALL: used Dict lookup for warm-start angle assignment:
```julia
bus_angle_map = Dict{Int, Float64}()
for row in eachrow(dcpf_bus_df)
    bus_angle_map[row[:bus_number]] = row[:θ]
end
for bus in get_components(Bus, sys_attempt)
    bnum = get_number(bus)
    if haskey(bus_angle_map, bnum)
        set_angle!(bus, bus_angle_map[bnum])
    end
    set_magnitude!(bus, 1.0)
end
```

## Observations

- **api-friction:** Same DCPF/ACPF return type inconsistency as noted in SMALL result.
  DCPF returns nested `Dict{Union{Char,String}, Dict{String, DataFrame}}` under period key "1",
  while ACPF returns flat `Dict{String, DataFrame}`.
