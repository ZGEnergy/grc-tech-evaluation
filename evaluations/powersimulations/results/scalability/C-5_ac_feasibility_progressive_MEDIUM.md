---
test_id: C-5
tool: powersimulations
dimension: scalability
network: MEDIUM
protocol_version: "v11"
skill_version: "v2"
test_hash: "bb82f193"
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 1.412
timing_source: measured
peak_memory_mb: 1189.2
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: binary_convergence_api
relaxation_level_achieved: "0% (nominal)"
loc: 269
solver: "PowerFlows.jl (built-in NR)"
cpu_threads_used: 1
cpu_threads_available: 32
timestamp: "2026-03-24T00:00:00Z"
---

# C-5: AC Feasibility -- Progressive Relaxation on MEDIUM

## Result: PASS

## Approach

Tested AC power flow convergence on the ACTIVSg 10,000-bus network (12,706 branches, 2,485
generators) using progressive thermal limit relaxation (0%, 10%, 20%). Same protocol as the
SMALL run: DCPF warm-start followed by ACPF attempts at each relaxation level.

**DCPF warm-start:** Solved `DCPowerFlow()` in 3.22s. Bus voltage angles ranged from -22.44
to +104.53 degrees. Set all voltage magnitudes to 1.0 pu.

**Optimization for 10k scale:** Used a `Dict{Int,Float64}` lookup for bus angles instead of
the nested-loop approach from the SMALL test (O(n) vs O(n^2) for bus-angle assignment).

**Solver:** PowerFlows.jl's built-in Newton-Raphson (no Ipopt needed for ACPF).

**Convergence evidence:** `binary_convergence_api` -- `solve_powerflow(ACPowerFlow(), sys)`
returns `nothing` on failure and a `Dict{String, DataFrame}` on success.

## Output

### DCPF Warm-Start

| Metric | Value |
|--------|-------|
| DCPF solve time | 3.22 s |
| Angle range | -22.44 to +104.53 degrees |

### Progressive Relaxation Results

| Relaxation | Converged | Wall-clock | Buses | Branches | VM range | Violations |
|------------|-----------|------------|-------|----------|----------|------------|
| 0% (nominal) | Yes | 1.41 s | 10,000 | 12,706 | 0.9002 - 1.0569 pu | 16 under + 3 over |
| 10% | Yes | 0.40 s | 10,000 | 12,706 | 0.9002 - 1.0569 pu | 16 under + 3 over |
| 20% | Yes | 0.38 s | 10,000 | 12,706 | 0.9002 - 1.0569 pu | 16 under + 3 over |

**Key finding:** ACPF converges at **0% relaxation (nominal thermal limits)** on MEDIUM.
No progressive relaxation was needed. All three relaxation levels converge to the same voltage
profile, consistent with SMALL behavior -- thermal limit relaxation only affects OPF branch
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
| DCPF time | 2.13 s | 3.22 s | 1.5x |
| ACPF time (first call) | 0.156 s | 1.41 s | 9.0x |
| ACPF time (JIT cached) | 0.049 s | 0.40 s | 8.2x |
| Peak memory | 1,163 MB | 1,189 MB | 1.0x |
| Voltage violations | 58 (2.9%) | 19 (0.19%) | - |

ACPF scales sub-linearly with network size for memory (nearly flat), but the solve time
increases roughly proportionally with the 5x bus count increase. The Newton-Raphson solver
in PowerFlows.jl handles 10k-bus networks efficiently.

## Workarounds

None required. Same clean API as SMALL.

## Timing

- **Wall-clock (ACPF, 0% relaxation):** 1.41 s (first call, includes JIT)
- **Wall-clock (ACPF, 10% relaxation):** 0.40 s (JIT cached)
- **Wall-clock (ACPF, 20% relaxation):** 0.38 s (JIT cached)
- **Wall-clock (DCPF warm-start):** 3.22 s
- **Wall-clock (total):** 29.2 s (includes 3x system loading for 10k network)
- **Timing source:** measured
- **Peak memory:** 1,189 MB (Julia process RSS)
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
