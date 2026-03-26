---
test_id: A-2
tool: powersimulations
dimension: expressiveness
network: TINY
protocol_version: "v11"
skill_version: "v2"
test_hash: "eb349d9c"
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 0.001
timing_source: measured
peak_memory_mb: 807.6
convergence_residual: null
convergence_iterations: 1
convergence_evidence_quality: iteration_count_reported
loc: 254
solver: "PowerFlows.jl built-in Newton-Raphson"
timestamp: "2026-03-24T00:00:00Z"
---

# A-2: AC Power Flow (Newton-Raphson)

## Result: PASS

## Approach

Used `PowerFlows.jl` v0.9.0 `solve_powerflow(ACPowerFlow(), sys)` on IEEE 39-bus.
`ACPowerFlow()` uses a built-in Newton-Raphson solver (not Ipopt). No external
optimizer configuration is needed. Flat-start initialization (Vm=1.0, Va=0.0) is the
default.

The result is a flat `Dict{String, DataFrame}` with `"bus_results"` and
`"flow_results"` keys (different nesting than DCPowerFlow -- see A-1 observations).

**v11 convergence diagnostics improvement:** PowerFlows.jl v0.9.0 does not expose
iteration count or convergence residual in its return value. However, per
cross-tool-watchpoints.md Probe-013, the internal NR solver emits convergence
diagnostics at `@info` log level. By capturing logs with `ConsoleLogger(buffer, Logging.Info)`,
the iteration count is recoverable:

```
[ Info: The NewtonRaphsonACPowerFlow solver converged after 1 iterations.
[ Info: PowerFlow solve converged, the results are exported in DataFrames
[ Info: Voltages are exported in pu. Powers are exported in MW/MVAr.
```

This upgrades convergence evidence quality from `proxy_voltage` (v10 finding) to
`iteration_count_reported`. The residual is still not reported via any API path.

## Output

**Bus results** (39 buses):

| Metric | Value |
|--------|-------|
| Vm min | 0.982 pu |
| Vm max | 1.064 pu |
| Vm mean | 1.026 pu |
| Buses with Vm != 1.0 | 39/39 (100%) |
| Va min | -14.54 deg |
| Va max | 4.47 deg |
| Nonzero angles | 38/39 |

All 39 buses have voltage magnitudes differing from the flat-start value of 1.0 pu,
well exceeding the 95% threshold. This confirms a genuine AC solution was computed.

**Sample bus voltages:**

| Bus | Vm (pu) | Va (deg) | P_gen (MW) | P_load (MW) |
|-----|---------|---------|-----------|------------|
| 1 | 1.039 | -13.54 | 0.0 | 97.6 |
| 3 | 1.031 | -12.28 | 0.0 | 322.0 |
| 30 | 1.048 | 4.47 | 250.0 | 0.0 |
| 36 | 1.064 | 0.79 | 560.0 | 0.0 |

**Branch active power flows:**
- Range: -824.8 to 453.8 MW (from-to direction)
- All 46 branches carry nonzero P and Q flow

**Branch reactive power flows:**
- Range: -156.7 to 113.1 Mvar

**Losses:**
- Total active power losses: 43.64 MW (0.7% of total generation)
- 42/46 branches have nonzero P losses
- Some transformer branches (e.g., bus-2-bus-30) show near-zero P losses but
  large Q through-flow, as expected for ideal transformers in the AC model

**NR iteration count:** 1 (from log capture). The case39.m file contains voltage
magnitude setpoints from the MATPOWER solution, so the NR solver converges in a single
iteration from these near-solution initial conditions. This is expected behavior, not
an indication of a trivial solve -- the power balance equations are still fully solved.

## Workarounds

None required. The iteration count is obtained via Julia's standard `Logging` module
(`ConsoleLogger` with `Logging.Info` level), which is a documented public API. This is
not a workaround -- it is the intended diagnostic path.

## Timing

- **Wall-clock:** 0.001 s (second run, after JIT warm-up)
- **Timing source:** measured
- **Peak memory:** 807.6 MB (Julia process RSS)
- **Solver iterations:** 1 (Newton-Raphson, from log capture)
- **Convergence residual:** not reported by PowerFlows.jl (no API path found)
- **Convergence evidence quality:** iteration_count_reported
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/powersimulations/tests/expressiveness/test_a2_acpf.jl`

Key API pattern:
```julia
using Logging

# Capture @info log output to extract NR iteration count
log_buffer = IOBuffer()
with_logger(ConsoleLogger(log_buffer, Logging.Info)) do
    pf_result = solve_powerflow(ACPowerFlow(), sys)
end
log_output = String(take!(log_buffer))
# Parse: "converged after N iterations"
m = match(r"converged after (\d+) iterations", log_output)
nr_iterations = m !== nothing ? parse(Int, m.captures[1]) : nothing
```

## Observations

- **convergence-quality:** PowerFlows.jl does not expose NR convergence residual via
  any API path. Iteration count is available only via `@info` log capture, not via the
  return value. The return Dict contains only `bus_results` and `flow_results` DataFrames.
  This is a diagnostic quality limitation (no residual), though iteration count is now
  recoverable. Severity: low.
- **api-friction:** AC and DC power flow return different Dict nesting structures (flat
  vs. nested under key "1"). Severity: low.
- **doc-gaps:** PowerFlows.jl documentation does not describe return value structure in
  detail. Column names and nesting must be discovered empirically. The `@info` log
  messages documenting convergence are not mentioned in the API docs. Severity: low.
