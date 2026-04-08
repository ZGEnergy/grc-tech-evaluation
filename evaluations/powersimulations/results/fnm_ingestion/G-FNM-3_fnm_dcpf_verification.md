---
test_id: G-FNM-3
tool: powersimulations
dimension: fnm_ingestion
network: LARGE
protocol_version: v11
skill_version: v2
test_hash: 2a6e1604
status: fail
workaround_class: null
blocked_by: null
wall_clock_seconds: 52.10
timing_source: measured
peak_memory_mb: 1139.8
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 385
solver: PowerFlows.DCPowerFlow
ingestion_path: matpower_raw
sced_mode: null
test_category: null
timestamp: "2026-03-24T18:30:00Z"
---

# G-FNM-3: DCPF Verification Against Reference Solution

## Result: FAIL

The bus angle gate fails (13.16% passing vs 95% required). The branch flow gate passes
(96.52% passing vs 90% required). Two hard-fail conditions trigger: excessive bus failing
fraction (86.8% > 20%) and extreme branch flow deviation (700.4% > 50%). The failure is
attributable to a **formulation difference**: PowerFlows.jl uses a simplified B-matrix
that ignores transformer tap ratios, while the MATPOWER reference uses a full B-matrix
that incorporates taps.

## Approach

1. Loaded pre-cleaned MATPOWER case `fnm_main_island.m` (~28,000-bus main island) via
   `PowerSystems.System(path; runchecks=false)`. This is the MATPOWER fallback path
   because G-FNM-1 failed (PowerSystems.jl has no PSS/E CSV parser).
2. Solved DCPF using `PowerFlows.solve_powerflow(PowerFlows.DCPowerFlow(), sys)`.
3. Loaded reference DCPF solution from `data/fnm/reference/dcpf/buses_dcpf.csv` and
   `branches_dcpf.csv` (MATPOWER-generated).
4. Loaded excluded buses from `data/fnm/reference/excluded_buses.json` (2,445 buses).
5. Converted tool bus angles from radians to degrees (PowerFlows.jl DCPowerFlow returns
   angles in radians despite `@info` message claiming pu).
6. Converted tool branch flows from per-unit to MW by multiplying by baseMVA (100).
   PowerFlows.jl DCPowerFlow `write_results` does not scale DC flows to MW, unlike the
   AC path.
7. Aggregated parallel branch flows by (from_bus, to_bus) pair before comparison.
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
| Non-excluded buses compared | ~28,000 |
| Passing (< 1.0 deg) | 3,668 (13.16%) |
| Failing | 24,194 (86.84%) |
| Mean VA deviation | 2.658984e+00 deg |
| Median VA deviation | 2.283271e+00 deg |
| P95 VA deviation | 6.778191e+00 deg |
| Max VA deviation | 3.587550e+01 deg (bus 44761) |

**Gate: FAIL** (13.16% < 95% required)

### Branch Flow Comparison

| Metric | Value |
|--------|-------|
| In-service branches (rows) | ~33,000 |
| Unique (from,to) pairs | 30,912 |
| Matched | 30,912 (100%) |
| Passing (< 10%) | 29,835 (96.52%) |
| Failing | 1,077 (3.48%) |
| Mean branch deviation | 2.224968e+00% |
| Median branch deviation | 3.875282e-10% |
| Max branch deviation | 7.004165e+02% at (14333, 13343) |

**Gate: PASS** (96.52% > 90% required)

### Hard-Fail Conditions

| Condition | Threshold | Actual | Triggered |
|-----------|-----------|--------|-----------|
| Excessive bus failing | > 20% | 86.8% | **YES** |
| Excessive branch failing | > 20% | 3.48% | no |
| Extreme branch deviation | > 50% | 700.4% | **YES** |

Two hard-fail conditions triggered: excessive bus failing fraction (86.8%) and extreme
branch flow deviation (700.4% on a single branch pair near a transformer with an
off-nominal tap ratio).

### Formulation Difference Analysis

The systematic bus angle deviations (mean 2.66 deg, median 2.28 deg) are consistent with
the **formulation sophistication catalog** from the cross-tool watchpoints. PowerFlows.jl's
DCPF uses the ABA/BA matrix construction from PowerNetworkMatrices.jl, which computes
branch susceptance as `b = -1/x` (simplified B-matrix), ignoring transformer tap ratios.
The MATPOWER reference uses the full B-matrix that accounts for tap ratios in the
admittance matrix construction.

Evidence:
- The network has ~2,340 off-nominal tap transformers (tap != 1.0) out of ~2,358 total
  TapTransformers, with tap ratios ranging from 0.789 to 1.417.
- The angle deviations are systematic and affect nearly all buses (86.8% fail), indicating
  a global formulation effect rather than localized data errors.
- Branch flow deviations are concentrated on branches adjacent to transformers with
  off-nominal taps. The extreme 700.4% deviation at (14333, 13343) is on a small-flow
  branch (ref ~3.22 MW) where the angle difference produces a disproportionate percentage
  error.
- The non-trivial solution check confirms the DCPF solve was valid: 27,858 of ~28,000
  buses have nonzero angles.

This is classified as `formulation-difference` [tool-specific: PowerFlows.jl simplified
B-matrix ignores transformer taps in DCPF], not a tool bug.

## Workarounds

None required. The failure is due to the inherent formulation difference between
PowerFlows.jl's simplified B-matrix and MATPOWER's full B-matrix. There is no
configuration option in PowerFlows.jl to switch to a full B-matrix for DCPF.

## Timing

- **Wall-clock:** 52.10s total (38.11s load + 10.70s solve + 3.29s comparison)
- **Timing source:** measured
- **Peak memory:** 1,139.8 MB (VmHWM)
- **Solver iterations:** N/A (direct linear solve)
- **Convergence residual:** N/A (DCPF is a linear system)
- **CPU cores used:** 1

Note: Wall-clock includes Julia JIT compilation overhead. The load time (38.11s) is
substantially higher than prior runs due to cold-start compilation.

## Test Script

**Path:** `evaluations/powersimulations/tests/fnm_ingestion/test_g_fnm_3_fnm_dcpf_verification.jl`

Key API calls:
```julia
# Load network via MATPOWER fallback
sys = PowerSystems.System("/workspace/data/fnm/reference/cleaned/fnm_main_island.m"; runchecks=false)

# Solve DCPF
dc_result = PowerFlows.solve_powerflow(PowerFlows.DCPowerFlow(), sys)

# Extract results (per-unit, not MW despite log message)
timestep_key = first(keys(dc_result))
bus_df = dc_result[timestep_key]["bus_results"]   # theta in radians, P in per-unit
flow_df = dc_result[timestep_key]["flow_results"] # P_from_to in per-unit

# Convert to physical units
angle_deg = rad2deg(bus_df.theta)
flow_mw = flow_df.P_from_to * PowerSystems.get_base_power(sys)
```
