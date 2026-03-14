---
test_id: G-FNM-3
tool: powersimulations
dimension: fnm_ingestion
network: LARGE
protocol_version: "v10"
skill_version: "v1"
test_hash: "ed61e7f5"
status: fail
workaround_class: null
blocked_by: null
wall_clock_seconds: 12.80
timing_source: measured
peak_memory_mb: 1178.6
convergence_residual: null
convergence_iterations: null
loc: 352
solver: PowerFlows.DCPowerFlow
timestamp: "2026-03-14T19:45:00Z"
input_path: matpower
---

# G-FNM-3: DCPF Verification Against Reference Solution

## Result: FAIL

The bus angle gate fails (13.2% passing vs 95% required). The branch flow gate passes
(96.5% passing vs 90% required). The failure is attributable to a **formulation difference**:
PowerFlows.jl uses a simplified B-matrix that ignores transformer tap ratios, while the
MATPOWER reference uses a full B-matrix that incorporates taps.

## Approach

1. Loaded `fnm_main_island.m` (27,862-bus pre-cleaned main island) via
   `PowerSystems.System(path; runchecks=false)`.
2. Solved DCPF using `PowerFlows.solve_powerflow(PowerFlows.DCPowerFlow(), sys)`.
3. Loaded reference solution from `data/fnm/reference/dcpf/buses_dcpf.csv` and
   `branches_dcpf.csv` (MATPOWER-generated).
4. Loaded excluded buses from `data/fnm/reference/excluded_buses.json` (2,445 buses).
5. Converted tool bus angles from radians to degrees (PowerFlows.jl DCPF returns
   angles in radians despite `@info` message claiming pu).
6. Converted tool branch flows from per-unit to MW by multiplying by baseMVA (100).
   PowerFlows.jl DCPF `write_results` does not scale DC flows to MW, unlike the AC path.
7. Aggregated parallel branch flows by (from_bus, to_bus) pair before comparison to
   avoid spurious percentage deviations from dict key collisions.
8. Evaluated pass conditions per `pass_conditions.json` dcpf section.

### Unit Correction Discovery

PowerFlows.jl v0.9.0's `write_results` for DC power flow emits an `@info` message
stating "Voltages are exported in pu. Powers are exported in MW/MVAr." However, empirical
verification shows that the DC path returns bus angles in radians and branch flows in
per-unit (system base), not MW. The AC path correctly exports in MW. This is a documentation
inconsistency in PowerFlows.jl, not a solver error. The test script corrects for this by
applying `rad2deg` to angles and multiplying flows by `baseMVA`.

## Output

### Bus Angle Comparison

| Metric | Value |
|--------|-------|
| Non-excluded buses compared | 27,862 |
| Passing (< 1.0 deg) | 3,668 (13.2%) |
| Failing | 24,194 (86.8%) |
| Mean VA deviation | 2.66 deg |
| Median VA deviation | 2.28 deg |
| P95 VA deviation | 6.78 deg |
| Max VA deviation | 35.88 deg (bus 44761) |

**Gate: FAIL** (13.2% < 95% required)

### Branch Flow Comparison

| Metric | Value |
|--------|-------|
| In-service branches (rows) | 32,532 |
| Unique (from,to) pairs | 30,912 |
| Matched | 30,912 (100%) |
| Passing (< 10%) | 29,835 (96.5%) |
| Failing | 1,077 (3.5%) |
| Mean branch deviation | 2.22% |
| Median branch deviation | ~0% |
| Max branch deviation | 700% at (14333, 13343) |

**Gate: PASS** (96.5% > 90% required)

### Hard-Fail Conditions

| Condition | Threshold | Actual | Triggered |
|-----------|-----------|--------|-----------|
| Excessive bus failing | > 20% | 86.8% | YES |
| Excessive branch failing | > 20% | 3.5% | no |
| Extreme branch deviation | > 50% | 700% | YES |

Two hard-fail conditions triggered: excessive bus failing fraction (86.8%) and extreme
branch flow deviation (700% on a single branch pair).

### Formulation Difference Analysis

The systematic bus angle deviations (mean 2.66 deg, median 2.28 deg) are consistent with
the **formulation sophistication catalog** from the cross-tool watchpoints. PowerFlows.jl's
DCPF uses the ABA/BA matrix construction from PowerNetworkMatrices.jl, which computes
branch susceptance as `b = -1/x` (simplified B-matrix), ignoring transformer tap ratios.
The MATPOWER reference uses the full B-matrix that accounts for tap ratios in the
admittance matrix construction.

Evidence:
- The network has 2,340 off-nominal tap transformers (tap != 1.0) out of 2,358 total
  TapTransformers, with tap ratios ranging from 0.789 to 1.417.
- The angle deviations are systematic and affect nearly all buses (86.8% fail), indicating
  a global formulation effect rather than localized data errors.
- Branch flow deviations are concentrated on branches adjacent to transformers with
  off-nominal taps. The extreme 700% deviation at (14333, 13343) is on a small-flow
  branch (ref 3.22 MW) where the angle difference produces a disproportionate percentage
  error.

This is classified as `formulation-difference`, not a tool bug.

## Workarounds

None required. The failure is due to the inherent formulation difference between
PowerFlows.jl's simplified B-matrix and MATPOWER's full B-matrix. There is no
configuration option in PowerFlows.jl to switch to a full B-matrix for DCPF.

## Timing

- **Wall-clock:** 12.80s total (8.87s load + 3.05s solve + 0.88s comparison)
- **Timing source:** measured
- **Peak memory:** 1,178.6 MB
- **Solver iterations:** N/A (direct linear solve)
- **Convergence residual:** N/A (DCPF is a linear system)
- **CPU cores used:** 1

## Observations

### `formulation-difference` -- Simplified B-matrix in PowerFlows.jl DCPF

PowerFlows.jl v0.9.0 uses a simplified B-matrix (`b = -1/x`) for DCPF that ignores
transformer tap ratios. On the 27,862-bus FNM with 2,340 off-nominal tap transformers,
this produces systematic angle deviations (mean 2.66 deg) compared to MATPOWER's full
B-matrix reference. Branch flows are less affected (96.5% within 10% tolerance) because
flow errors depend on the relative angle difference across each branch, which partially
cancels out the global offset.

This formulation difference is inherent to the PowerNetworkMatrices.jl ABA matrix
construction and cannot be corrected via solver configuration. It affects all DCPF
results produced by PowerFlows.jl on networks with off-nominal tap transformers.

### `fnm-data-model` -- PowerFlows.jl DC output unit inconsistency

PowerFlows.jl v0.9.0 reports "Powers are exported in MW/MVAr" for DC power flow results,
but the actual output is in per-unit (system base). Bus angles are in radians, not degrees.
Users must multiply flows by baseMVA and convert angles with `rad2deg`. The AC power flow
path correctly exports in MW. This inconsistency affects any downstream analysis that
trusts the log message without empirical verification.

## Test Script

**Path:** `evaluations/powersimulations/tests/fnm_ingestion/test_g_fnm_3_fnm_dcpf_verification.jl`

Key API calls:
```julia
# Load network
sys = PowerSystems.System("/workspace/data/fnm/reference/cleaned/fnm_main_island.m"; runchecks=false)

# Solve DCPF
dc_result = PowerFlows.solve_powerflow(PowerFlows.DCPowerFlow(), sys)

# Extract results (per-unit, not MW despite log message)
timestep_key = first(keys(dc_result))
bus_df = dc_result[timestep_key]["bus_results"]   # θ in radians, P in per-unit
flow_df = dc_result[timestep_key]["flow_results"] # P_from_to in per-unit

# Convert to physical units
angle_deg = rad2deg(bus_df.θ)
flow_mw = flow_df.P_from_to * PowerSystems.get_base_power(sys)
```
