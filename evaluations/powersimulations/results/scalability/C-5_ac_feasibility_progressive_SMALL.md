---
test_id: C-5
tool: powersimulations
dimension: scalability
network: SMALL
protocol_version: "v11"
skill_version: "v2"
test_hash: "bb82f193"
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 0.156
timing_source: measured
peak_memory_mb: 1162.9
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: binary_convergence_api
relaxation_level_achieved: "0% (nominal)"
loc: 271
solver: "PowerFlows.jl (built-in NR)"
cpu_threads_used: 1
cpu_threads_available: 32
timestamp: "2026-03-24T00:00:00Z"
---

# C-5: AC Feasibility -- Progressive Relaxation on SMALL

## Result: PASS

## Approach

Tested AC power flow convergence on the ACTIVSg 2000-bus network using progressive thermal
limit relaxation (0%, 10%, 20%). The protocol calls for DCPF warm-start followed by ACPF
attempts at each relaxation level.

**DCPF warm-start:** Solved `DCPowerFlow()` to obtain bus voltage angles. Set all voltage
magnitudes to 1.0 pu (DCPF does not produce magnitudes). Angles ranged from -35.34 to +41.73
degrees.

**Progressive relaxation:** For each relaxation level (0%, 10%, 20%), loaded a fresh system,
applied DCPF warm-start angles via `set_angle!` on each bus, optionally relaxed branch thermal
limits by the specified factor via `set_rating!`, then attempted `ACPowerFlow()`.

**Solver:** PowerFlows.jl v0.9.0 built-in Newton-Raphson solver. Ipopt is not needed for ACPF
(only for AC OPF). Newton-Raphson is single-threaded.

**JIT handling:** A warm-up ACPF solve was run before the timed attempts to compile all relevant
Julia methods. Timed attempts exclude JIT compilation overhead.

## Output

### DCPF Warm-Start

| Metric | Value |
|--------|-------|
| DCPF solve time | 2.09 s |
| Angle range | -35.34 to +41.73 degrees |

### Progressive Relaxation Results

| Relaxation | Converged | Wall-clock (s) | Buses | Branches | VM range (pu) | Under-voltage violations |
|------------|-----------|----------------|-------|----------|---------------|--------------------------|
| 0% (nominal) | Yes | 0.049 | 2000 | 3206 | 0.9362 - 1.0161 | 58 buses < 0.95 pu |
| 10% | Yes | 0.057 | 2000 | 3206 | 0.9362 - 1.0161 | 58 buses < 0.95 pu |
| 20% | Yes | 0.050 | 2000 | 3206 | 0.9362 - 1.0161 | 58 buses < 0.95 pu |

**Key finding:** ACPF converges at **0% relaxation (nominal thermal limits)** on SMALL with
DCPF warm-start. No progressive relaxation was needed. All three relaxation levels converge
to the identical voltage profile, which is expected since thermal limit relaxation affects OPF
branch flow constraints, not the Newton-Raphson power balance equations.

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

### Convergence Evidence

Convergence is verified via `binary_convergence_api` tier: `solve_powerflow(ACPowerFlow(), sys)`
returns `nothing` on failure and a `Dict{String, DataFrame}` on success. The non-nothing
return confirms convergence. Additionally, 80% of bus voltage magnitudes differ from the
flat-start value of 1.0 pu, satisfying the proxy_voltage cross-check.

PowerFlows.jl v0.9.0 does not expose the Newton-Raphson residual in its return value (see
[convergence-quality observation](../observations/convergence-quality-expressiveness-A-2_acpf.md)
from A-2). Iteration count is available via Julia `@info` log capture but was not captured
in this run to keep timing clean.

## Workarounds

None required.

## Timing

- **Wall-clock (ACPF, 0% relaxation):** 0.049 s (after JIT warm-up)
- **Wall-clock (ACPF, 10% relaxation):** 0.057 s
- **Wall-clock (ACPF, 20% relaxation):** 0.050 s
- **Wall-clock (sum of three ACPF attempts):** 0.156 s
- **Wall-clock (DCPF warm-start):** 2.094 s
- **Wall-clock (total including system loads):** 15.9 s
- **Timing source:** measured
- **Peak memory:** 1,162.9 MB (Julia process RSS)
- **CPU threads used:** 1 (NR is single-threaded)
- **CPU threads available:** 32

## Test Script

**Path:** `evaluations/powersimulations/tests/scalability/test_c5_ac_feasibility_progressive_SMALL.jl`

Key API pattern:
```julia
# DCPF warm-start
dcpf_result = solve_powerflow(DCPowerFlow(), sys)
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

# ACPF — returns Dict{String, DataFrame} on success, nothing on failure
pf_result = solve_powerflow(ACPowerFlow(), sys)
```

## Observations

- **api-friction:** `DCPowerFlow()` and `ACPowerFlow()` return different result structures.
  DCPF returns `Dict{Union{Char,String}, Dict{String, DataFrame}}` (nested under period key "1"),
  while ACPF returns `Dict{String, DataFrame}` (flat). This inconsistency requires careful handling.
- **doc-gaps:** The return type difference between `DCPowerFlow` and `ACPowerFlow` is not
  documented in PowerFlows.jl's API reference. Discovered empirically via `KeyError`.
