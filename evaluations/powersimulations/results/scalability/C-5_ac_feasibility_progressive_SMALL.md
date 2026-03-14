---
test_id: C-5
tool: powersimulations
dimension: scalability
network: SMALL
protocol_version: "v10"
skill_version: "v1"
test_hash: "878fdc60"
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 0.740
timing_source: measured
peak_memory_mb: 1134.5
convergence_residual: null
convergence_iterations: null
relaxation_level_achieved: "0% (nominal)"
loc: 257
solver: PowerFlows.jl (built-in NR)
timestamp: "2026-03-14T00:00:00Z"
---

# C-5: AC Feasibility — Progressive Relaxation on SMALL

## Result: PASS

## Approach

Tested AC power flow convergence on the ACTIVSg 2000-bus network using progressive thermal
limit relaxation (0%, 10%, 20%). The protocol calls for DCPF warm-start followed by ACPF
attempts at each relaxation level.

**DCPF warm-start:** Solved `DCPowerFlow()` to obtain bus voltage angles. Set all voltage
magnitudes to 1.0 pu (DCPF doesn't produce magnitudes). Angles ranged from -35.34 to +41.73
degrees.

**Progressive relaxation:** For each relaxation level (0%, 10%, 20%), loaded a fresh system,
applied DCPF warm-start angles, optionally relaxed branch thermal limits by the specified
factor, then attempted `ACPowerFlow()`.

**Solver:** PowerFlows.jl's built-in Newton-Raphson (no Ipopt needed for ACPF). Ipopt would
be needed for AC OPF, not for AC power flow.

## Output

### DCPF Warm-Start

| Metric | Value |
|--------|-------|
| DCPF solve time | 2.13 s |
| Angle range | -35.34 to +41.73 degrees |

### Progressive Relaxation Results

| Relaxation | Converged | Wall-clock | Buses | Branches | VM range | Violations |
|------------|-----------|------------|-------|----------|----------|------------|
| 0% (nominal) | Yes | 0.74 s | 2000 | 3206 | 0.9362 - 1.0161 pu | 58 under-voltage |
| 10% | Yes | 0.049 s | 2000 | 3206 | 0.9362 - 1.0161 pu | 58 under-voltage |
| 20% | Yes | 0.049 s | 2000 | 3206 | 0.9362 - 1.0161 pu | 58 under-voltage |

**Key finding:** ACPF converges at **0% relaxation (nominal thermal limits)** on SMALL.
No progressive relaxation was needed. All three relaxation levels converge to the same
voltage profile, which is expected since thermal limit relaxation only affects OPF branch
constraints, not the power flow equations themselves.

### Voltage Profile

| Statistic | Value |
|-----------|-------|
| Min VM | 0.9362 pu |
| Max VM | 1.0161 pu |
| Mean VM | 0.9825 pu |
| Buses with VM != 1.0 | 1,601 of 2,000 (80%) |
| Under-voltage (< 0.95 pu) | 58 buses |
| Over-voltage (> 1.05 pu) | 0 buses |

The voltage profile shows genuine convergence: 80% of buses have voltage magnitudes different
from the flat-start value of 1.0 pu, and the minimum voltage (0.9362 pu) is well below 0.95,
indicating real reactive power flow computation. The 58 under-voltage buses suggest the network
has areas with insufficient reactive support, a realistic characteristic of the ACTIVSg 2k
test case.

### Timing Notes

The first ACPF attempt (0% relaxation) takes 0.74s while subsequent attempts take ~0.05s.
This is due to Julia JIT compilation on the first call. The test used a fresh system load
for each attempt to avoid state contamination, but the JIT compilation was already cached
from the first call.

## Workarounds

None required.

## Timing

- **Wall-clock (ACPF, 0% relaxation):** 0.74 s (first call, includes JIT)
- **Wall-clock (ACPF, 10% relaxation):** 0.049 s (JIT cached)
- **Wall-clock (ACPF, 20% relaxation):** 0.048 s (JIT cached)
- **Wall-clock (DCPF warm-start):** 2.13 s
- **Wall-clock (total):** 15.1 s (includes 3x system loading)
- **Timing source:** measured
- **Peak memory:** 1,134.5 MB (Julia process RSS)
- **CPU cores used:** 1 (32 available)

## Test Script

**Path:** `evaluations/powersimulations/tests/scalability/test_c5_ac_feasibility_progressive_SMALL.jl`

Key API pattern:
```julia
# DCPF warm-start
dcpf_result = solve_powerflow(DCPowerFlow(), sys)
# Note: returns Dict{Union{Char,String}, Dict{String, DataFrame}} with period key "1"
dcpf_bus_df = dcpf_result["1"]["bus_results"]

# Apply warm-start angles to fresh system
for row in eachrow(dcpf_bus_df)
    for bus in get_components(Bus, sys_attempt)
        if get_number(bus) == row[:bus_number]
            set_angle!(bus, row[:θ])
            set_magnitude!(bus, 1.0)
            break
        end
    end
end

# ACPF — returns Dict{String, DataFrame} (flat, not nested like DCPF)
pf_result = solve_powerflow(ACPowerFlow(), sys)
```

## Observations

- **api-friction:** `DCPowerFlow()` and `ACPowerFlow()` return different result structures.
  DCPF returns `Dict{Union{Char,String}, Dict{String, DataFrame}}` (nested under period key "1"),
  while ACPF returns `Dict{String, DataFrame}` (flat). This inconsistency is a minor API
  friction point that requires careful handling.
- **doc-gaps:** The return type difference between `DCPowerFlow` and `ACPowerFlow` is not
  documented in PowerFlows.jl's API reference. Discovered empirically via `KeyError`.
