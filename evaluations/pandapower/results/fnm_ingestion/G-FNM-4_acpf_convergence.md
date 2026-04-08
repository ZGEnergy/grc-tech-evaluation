---
test_id: G-FNM-4
tool: pandapower
dimension: fnm_ingestion
network: LARGE
protocol_version: "v11"
skill_version: "v2"
test_hash: "bd023e12"
status: informational
workaround_class: stable
blocked_by: null
wall_clock_seconds: 15.93
timing_source: measured
peak_memory_mb: 97.1
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 228
solver: null
ingestion_path: matpower_raw
input_path: matpower
relaxation_level_achieved: infeasible
dcpf_init_mean_deg: 209.5
dcpf_init_max_abs_deg: 536.9
acpf_timeout_minutes: 30
timestamp: 2026-03-24T12:00:00Z
---

# G-FNM-4: ACPF Convergence -- DCPF Warm-Start + Progressive Relaxation

## Result: INFORMATIONAL

ACPF did not converge at any relaxation level (0%, 10%, 20%). The
`relaxation_level_achieved` is **infeasible**. pandapower's Newton-Raphson
solver reaches 100 iterations without convergence on this ~28,000-bus FNM
main island network at all three relaxation levels.

## Approach

1. Loaded the pre-cleaned MATPOWER case (`fnm_main_island.m`, ~28,000-bus
   main island) using `matpowercaseframes.CaseFrames` + `from_ppc`
   (same MATPOWER fallback path as G-FNM-1/G-FNM-3).
2. Solved DCPF via `pandapower.rundcpp(net)` -- converges successfully.
3. Attempted ACPF at 0% relaxation with `pandapower.runpp(net,
   init="results", algorithm="nr", max_iteration=100, tolerance_mva=1e-6,
   enforce_q_lims=True)` to use DCPF angles as warm-start.
4. After failure at 0%, re-solved DCPF, multiplied all branch thermal
   limits by 1.10, and retried ACPF (10% relaxation).
5. After failure at 10%, reset limits, re-solved DCPF, multiplied limits
   by 1.20, and retried (20% relaxation).
6. All three relaxation levels failed to converge.

## Output

### DCPF Warm-Start Statistics

| Metric | Value |
|--------|-------|
| DCPF converged | yes |
| DCPF solve time | 2.61 s |
| DCPF mean |VA| (all buses) | 2.095060e+02 deg |
| DCPF max |VA| | 5.369341e+02 deg |

The large DCPF voltage angles (max 5.369341e+02 degrees) indicate unusual
operating conditions in the network -- angles exceeding 360 degrees suggest
either a topology anomaly or a localized sub-region with extreme angle
differences. This is consistent with the localized data ingestion issues
identified in G-FNM-3 (101 buses with 14-21 degree systematic deviations
from reference).

### Progressive Relaxation Results

| Step | Relaxation | Converged | Wall-Clock (s) | Error |
|------|------------|-----------|----------------|-------|
| 2 | 0% | No | 4.26 | NR did not converge after 100 iterations |
| 3 | 10% | No | 0.54 | NR did not converge after 100 iterations |
| 4 | 20% | No | 0.82 | NR did not converge after 100 iterations |

### Relaxation Level Achieved

**infeasible** -- ACPF did not converge at any relaxation level.

## Analysis of Non-Convergence

The ACPF non-convergence is attributable to a combination of factors:

1. **Data ingestion path limitations.** pandapower ingests the FNM via
   the MATPOWER PPC path, which flattens transformer-specific data
   (tap control modes, winding impedance details, switched shunt
   discrete steps) and aggregates loads per bus. This data loss reduces
   the fidelity of the AC model compared to the original PSS/E source.
   [tool-specific: PPC import flattens transformer data]

2. **Localized topology anomalies.** G-FNM-3 identified a cluster of
   ~101 buses with systematic angle deviations of 14-21 degrees.
   These buses, sitting in a connected sub-region of the
   subtransmission/distribution network (69-138 kV), likely create
   numerical ill-conditioning in the AC Jacobian.

3. **Q-limit interpretation.** The PPC import path may incorrectly
   interpret zero reactive power limits (QT=0, QB=0) as zero reactive
   capability rather than "unlimited," preventing generators at PV
   buses from providing the reactive support needed for voltage
   regulation. This is a known cross-tool pitfall documented in the
   evaluation watchpoints.

4. **pandapower does not use Ipopt for ACPF.** pandapower's `runpp()` uses
   its own internal Newton-Raphson implementation (with PYPOWER heritage),
   not an external NLP solver. There is no Ipopt integration for power
   flow (only for OPF via PandaModels.jl). The internal NR
   implementation may have less robust convergence characteristics on
   ill-conditioned networks compared to Ipopt with MUMPS.
   [tool-specific: internal NR only, no Ipopt for ACPF]

## Workarounds

1. **MATPOWER fallback** (stable):
   - **What:** Used pre-cleaned `fnm_main_island.m` via `matpowercaseframes` and `from_ppc` instead of intermediate CSVs.
   - **Why:** pandapower has no native CSV import.
   - **Durability:** stable -- public, documented APIs.
   - **Grade impact:** Reduces field fidelity (PPC format flattens
     transformer data), which may contribute to ACPF non-convergence.

2. **Zero RATE_A fix** (stable):
   - **What:** Set zero RATE_A values to 9999 before `from_ppc`.
   - **Why:** pandapower 3.4.0 bug in `_from_ppc_branch`.
   - **Durability:** stable.

## Timing

- **Wall-clock:** 15.93 s (total: load + DCPF + 3 ACPF attempts)
- **Timing source:** measured (time.perf_counter)
- **Peak memory:** 97.1 MB
- **Solver iterations:** 100 per attempt (all failed)
- **Convergence residual:** N/A (did not converge)
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pandapower/tests/fnm_ingestion/test_g_fnm_4_acpf_convergence.py`
