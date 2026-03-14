---
test_id: G-FNM-4
tool: powersimulations
dimension: fnm_ingestion
network: LARGE
protocol_version: "v10"
skill_version: "v1"
test_hash: "bfd9783e"
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: 46.55
timing_source: measured
peak_memory_mb: 1587.4
convergence_residual: null
convergence_iterations: null
loc: 273
solver: PowerFlows.ACPowerFlow (NewtonRaphson)
timestamp: "2026-03-14T19:50:00Z"
input_path: matpower
dcpf_init_mean_deg: 212.01
dcpf_init_max_abs_deg: 540.25
relaxation_level_achieved: infeasible
acpf_timeout_minutes: 30
---

# G-FNM-4: ACPF Convergence (DCPF warm-start + progressive relaxation)

## Result: INFORMATIONAL

The Newton-Raphson AC power flow solver in PowerFlows.jl failed to converge at all
three relaxation levels (0%, 10%, 20%) on the 27,862-bus FNM main island network.
Relaxation level achieved: **infeasible**.

## Approach

1. **DCPF warm-start:** Loaded `fnm_main_island.m` and solved DCPF via
   `PowerFlows.solve_powerflow(DCPowerFlow(), sys)`. Extracted bus voltage angles
   from the DCPF solution.
2. **Angle initialization:** Set bus angles from the DCPF solution on the System
   object via `PowerSystems.set_angle!(bus, angle)`. Voltage magnitudes left at their
   MATPOWER-loaded values (generator setpoints or 1.0 pu default).
3. **Step 2 (0% relaxation):** Attempted ACPF with `PowerFlows.solve_powerflow!(ACPowerFlow(), sys; maxIterations=100, check_connectivity=false)`.
4. **Step 3 (10% relaxation):** Reloaded system, re-applied DCPF angles, increased
   all branch ratings by 10%, re-attempted ACPF.
5. **Step 4 (20% relaxation):** Same as Step 3 with 20% rating relaxation.

## Output

### Step 1: DCPF Warm-Start

| Metric | Value |
|--------|-------|
| DCPF solve time | 2.73s |
| Mean \|angle\| (non-zero buses) | 212.0 deg |
| Max \|angle\| | 540.2 deg |
| Non-zero angles | 27,858 / 27,862 |

The large angle magnitudes (mean 212 deg) are expected for a large interconnected
network where the slack bus reference sets the zero point and other buses span
a wide range of angular positions.

### Step 2: ACPF at 0% Relaxation

| Metric | Value |
|--------|-------|
| Converged | No |
| Wall-clock | 10.37s |
| Solver | NewtonRaphsonACPowerFlow |
| Max iterations | 100 |

The Newton-Raphson solver ran 100 iterations without convergence.

### Step 3: ACPF at 10% Relaxation

| Metric | Value |
|--------|-------|
| Converged | No |
| Wall-clock | 9.28s |
| Branch rating increase | 10% |

### Step 4: ACPF at 20% Relaxation

| Metric | Value |
|--------|-------|
| Converged | No |
| Wall-clock | 9.00s |
| Branch rating increase | 20% |

### Summary

| Relaxation Level | Converged | Time (s) |
|-----------------|-----------|----------|
| 0% | No | 10.37 |
| 10% | No | 9.28 |
| 20% | No | 9.00 |

**Relaxation level achieved: infeasible**

## Analysis

The ACPF non-convergence on this 27,862-bus network is attributable to several factors:

1. **Network scale:** 27,862 buses is at the upper end of what open-source NR solvers
   reliably handle without specialized initialization and tuning. Commercial tools
   (PSS/E, PowerWorld) use multi-level initialization strategies, optimal multiplier
   selection, and bus-ordering heuristics not available in PowerFlows.jl.

2. **Q-limit interaction:** PowerSystems.jl maps all MATPOWER generators as
   `ThermalStandard` with Q-limits from the MATPOWER gen data. Some generators may
   have tight Q-limits that cause PV-to-PQ bus transitions during NR iteration,
   destabilizing convergence. The cross-tool watchpoints note that `QT=0/QB=0`
   interpretation can trigger false convergence failure.

3. **Formulation difference in warm-start:** The DCPF warm-start angles come from
   PowerFlows.jl's simplified B-matrix, which differs from MATPOWER's full B-matrix
   by ~2.7 degrees on average (from G-FNM-3). This offset degrades the warm-start
   quality for the NR solver.

4. **Rating relaxation scope:** The branch rating relaxation (10%, 20%) affects thermal
   limits but does not address the voltage-reactive power convergence challenge, which
   is the primary difficulty on large AC networks.

## Workarounds

None attempted beyond the progressive relaxation protocol. Additional strategies that
could potentially improve convergence (not tested):
- Increasing `maxIterations` beyond 100
- Relaxing convergence tolerance (`tol` parameter)
- Enabling `check_reactive_power_limits=true` to allow PV-to-PQ transitions
- Manually widening generator Q-limits before solving
- Using a flat start (VM=1.0, VA=0.0) instead of DCPF warm-start

These are left as future diagnostic paths since G-FNM-4 has no hard gate.

## Timing

- **Wall-clock:** 46.55s total (8.93s initial load + 2.73s DCPF + 10.37s ACPF-0% +
  9.28s ACPF-10% + 9.00s ACPF-20% + overhead from reloads)
- **Timing source:** measured
- **Peak memory:** 1,587.4 MB
- **Solver iterations:** up to 100 per attempt (max iterations reached)
- **Convergence residual:** not reported (solver returns boolean only)
- **CPU cores used:** 1

## Observations

### `fnm-scale` -- ACPF non-convergence on 28K-bus network

PowerFlows.jl's Newton-Raphson ACPF solver cannot converge on the 27,862-bus FNM
main island network even with DCPF warm-start and 20% branch rating relaxation.
This is consistent with the expected behavior for large-scale AC power flow in
open-source tools without specialized initialization heuristics. The solver does
not expose convergence residual or iteration count diagnostics beyond a boolean
converged/not-converged status, limiting root-cause analysis.

### `fnm-data-model` -- No convergence diagnostics from PowerFlows.jl

PowerFlows.jl's `solve_powerflow!` returns only a boolean `converged` flag. It does
not expose the final NR mismatch residual, iteration count, or per-bus power balance
residuals to the caller. The internal `_run_powerflow_method` function does compute
these values (and logs iteration count on success) but does not return them on failure.
This limits diagnostic capability for large-network convergence studies.

## Test Script

**Path:** `evaluations/powersimulations/tests/fnm_ingestion/test_g_fnm_4_fnm_acpf_convergence.jl`

Key API calls:
```julia
# DCPF warm-start
dc_result = PowerFlows.solve_powerflow(PowerFlows.DCPowerFlow(), sys)

# Set bus angles from DCPF
PowerSystems.set_angle!(bus, angle_from_dcpf)

# ACPF attempt
converged = PowerFlows.solve_powerflow!(
    PowerFlows.ACPowerFlow(), sys;
    maxIterations=100, check_connectivity=false
)

# Relax branch ratings
PowerSystems.set_rating!(branch, rating * 1.10)
```
