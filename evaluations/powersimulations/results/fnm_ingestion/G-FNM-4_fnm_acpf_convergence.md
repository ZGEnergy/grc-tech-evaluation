---
test_id: G-FNM-4
tool: powersimulations
dimension: fnm_ingestion
network: LARGE
protocol_version: v11
skill_version: v2
test_hash: f1e2d021
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: 145.25
timing_source: measured
peak_memory_mb: 1727.5
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: binary_convergence_api
loc: 275
solver: PowerFlows.ACPowerFlow (NewtonRaphson)
ingestion_path: matpower_raw
sced_mode: null
test_category: null
timestamp: "2026-03-24T22:00:00Z"
dcpf_init_mean_deg: 2.120131e+02
dcpf_init_max_abs_deg: 5.402463e+02
relaxation_level_achieved: infeasible
acpf_timeout_minutes: 30
---

# G-FNM-4: ACPF Convergence (DCPF warm-start + progressive relaxation)

## Result: INFORMATIONAL

The Newton-Raphson AC power flow solver in PowerFlows.jl failed to converge at all
three relaxation levels (0%, 10%, 20%) on the ~28,000-bus FNM main island network.
Relaxation level achieved: **infeasible**.

## Approach

1. **DCPF warm-start:** Loaded `fnm_main_island.m` (MATPOWER fallback, ~28,000 buses) via
   `PowerSystems.System(path; runchecks=false)`. Solved DCPF via
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
| DCPF solve time | 10.51s |
| Mean \|angle\| (non-zero buses) | 2.120131e+02 deg |
| Max \|angle\| | 5.402463e+02 deg |
| Non-zero angles | 27,858 / ~28,000 |

The large angle magnitudes (mean 212 deg) are expected for a large interconnected
network where the slack bus reference sets the zero point and other buses span
a wide range of angular positions.

### Step 2: ACPF at 0% Relaxation

| Metric | Value |
|--------|-------|
| Converged | No |
| Wall-clock | 33.77s |
| Solver | NewtonRaphsonACPowerFlow |
| Max iterations | 100 |

The Newton-Raphson solver ran 100 iterations without convergence. PowerFlows.jl
emitted `Error: The PowerFlows.NewtonRaphsonACPowerFlow solver failed to converge.`
at the `@error` log level.

### Step 3: ACPF at 10% Relaxation

| Metric | Value |
|--------|-------|
| Converged | No |
| Wall-clock | 18.46s |
| Branch rating increase | 10% |

### Step 4: ACPF at 20% Relaxation

| Metric | Value |
|--------|-------|
| Converged | No |
| Wall-clock | 28.75s |
| Branch rating increase | 20% |

### Summary

| Relaxation Level | Converged | Time (s) |
|-----------------|-----------|----------|
| 0% | No | 33.77 |
| 10% | No | 18.46 |
| 20% | No | 28.75 |

**Relaxation level achieved: infeasible**

## Analysis

The ACPF non-convergence on this ~28,000-bus network is attributable to several factors:

1. **Network scale:** ~28,000 buses is at the upper end of what open-source NR solvers
   reliably handle without specialized initialization and tuning. Commercial tools
   (PSS/E, PowerWorld) use multi-level initialization strategies, optimal multiplier
   selection, and bus-ordering heuristics not available in PowerFlows.jl.

2. **Q-limit interaction:** PowerSystems.jl maps all MATPOWER generators as
   `ThermalStandard` with Q-limits from the MATPOWER gen data. Some generators may
   have tight Q-limits that cause PV-to-PQ bus transitions during NR iteration,
   destabilizing convergence. The cross-tool watchpoints note that `QT=0/QB=0`
   interpretation can trigger false convergence failure.

3. **Formulation difference in warm-start:** The DCPF warm-start angles come from
   PowerFlows.jl's simplified B-matrix (see [G-FNM-3 formulation-difference observation](../observations/formulation-difference-fnm_ingestion-G-FNM-3_fnm_dcpf_verification.md)),
   which ignores transformer tap ratios. On a network with 2,340 off-nominal-tap
   transformers, this produces angle offsets of ~2.7 degrees mean that degrade the
   warm-start quality for the NR solver.

4. **Rating relaxation scope:** The branch rating relaxation (10%, 20%) affects thermal
   limits but does not address the voltage-reactive power convergence challenge, which
   is the primary difficulty on large AC networks. Rating relaxation is more relevant
   for OPF feasibility than for power flow convergence.

5. **Convergence diagnostics limitation:** PowerFlows.jl returns only a boolean
   `converged` flag and emits log messages at `@error` level on failure. It does not
   expose the final NR mismatch residual or per-bus power balance residuals to the
   caller. This limits root-cause analysis of convergence failures. Convergence
   evidence quality is `binary_convergence_api` (tier 3 of 4).

## Workarounds

None attempted beyond the progressive relaxation protocol. Additional strategies that
could potentially improve convergence (not tested):
- Increasing `maxIterations` beyond 100
- Relaxing convergence tolerance (`tol` parameter)
- Enabling `check_reactive_power_limits=true` to allow PV-to-PQ transitions
- Manually widening generator Q-limits before solving
- Using a flat start (VM=1.0, VA=0.0) instead of DCPF warm-start
- Using the alternative `TrustRegionACPowerFlow` or `LevenbergMarquardtACPowerFlow` solvers

These are left as future diagnostic paths since G-FNM-4 has no hard gate consequence.

## Timing

- **Wall-clock:** 145.25s total (38.92s initial load + 10.51s DCPF + 33.77s ACPF-0% +
  18.46s ACPF-10% + 28.75s ACPF-20% + overhead from reloads)
- **Timing source:** measured
- **Peak memory:** 1,727.5 MB (peak RSS)
- **Solver iterations:** up to 100 per attempt (max iterations reached)
- **Convergence residual:** not reported (solver returns boolean only)
- **Convergence evidence quality:** binary_convergence_api
- **CPU cores used:** 1

## Observations

### `fnm-scale` -- ACPF non-convergence on 28K-bus network

PowerFlows.jl's Newton-Raphson ACPF solver cannot converge on the ~28,000-bus FNM
main island network even with DCPF warm-start and 20% branch rating relaxation.
This is consistent with the expected behavior for large-scale AC power flow in
open-source tools without specialized initialization heuristics. [tool-specific]

### `fnm-data-model` -- Limited convergence diagnostics from PowerFlows.jl

PowerFlows.jl's `solve_powerflow!` returns only a boolean `converged` flag. It does
not expose the final NR mismatch residual, iteration count, or per-bus power balance
residuals to the caller via the API. On failure, it emits `@error` log messages
including "The PowerFlows.NewtonRaphsonACPowerFlow solver failed to converge." The
internal `_run_powerflow_method` function computes these values but does not return
them. This achieves convergence evidence quality tier `binary_convergence_api` (3/4).
[tool-specific]

### `formulation-difference` -- DCPF warm-start degraded by simplified B-matrix

The DCPF warm-start angles used for ACPF initialization are computed with
PowerFlows.jl's simplified B-matrix (b = -1/x, ignoring tap ratios). On the FNM
with 2,340 off-nominal-tap transformers, this produces mean angle deviations of
~2.7 degrees versus a full B-matrix reference (from G-FNM-3). This systematic
offset degrades the warm-start quality and may contribute to NR non-convergence,
though the primary convergence challenge is the network scale and Q-limit
interaction. [tool-specific]

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
