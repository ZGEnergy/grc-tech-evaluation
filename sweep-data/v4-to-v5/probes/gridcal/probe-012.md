---
probe_id: probe-012
tool: gridcal
source_test: B-9
probe_type: convergence_check
classification: claim_supported
reason: "Reproduced max diff of 743.46 MW (LA vs DCPF) and 15139.36 MW (PTDF@Sbus vs DCPF), matching original claim exactly"
solver_version: "5.6.28"
solver_version_match: true
timeout_seconds: 300
wall_clock_seconds: 22.71
timestamp: 2026-03-09T00:00:00Z
---

# Probe probe-012: PTDF flow predictions diverge from DCPF by up to 743 MW on MEDIUM

## Original Claim

From `evaluations/gridcal/results/extensibility/B-9_ptdf_extraction_MEDIUM.md`:

> LA direct flows vs DCPF: max abs diff 743.46 MW, mean abs diff 2.68 MW.
> PTDF @ Sbus vs DCPF: max abs diff 15,139.36 MW, mean abs diff 29.57 MW.
> Scored as qualified_pass because PTDF matrix is accessible and dimensions are correct,
> but flow prediction mismatch on the large network prevents full pass.

## Probe Methodology

Wrote a standalone script that:
1. Loads the ACTIVSg 10k-bus network in GridCal (veragridengine 5.6.28)
2. Runs DCPF (SolverType.Linear) to get reference flows
3. Runs LinearAnalysis (vge.linear_power_flow) to get PTDF and LA direct flows
4. Compares LA direct flows vs DCPF flows
5. Computes PTDF @ Sbus and compares to DCPF flows
6. Investigates root cause: island count, transformer tap correlation, slack bus effects

Script path: `sweep-data/v4-to-v5/probes/gridcal/probe-012_script.py`

Executed via:

```
.devcontainer/dc-exec -C /workspace/evaluations/gridcal timeout 300 uv run python -c "$(cat script)"
```

## Probe Results

```
GridCal (veragridengine) version: 5.6.28
Network: 10000 buses, 12706 branches (9726 lines, 2980 transformers)
Islands: 1

--- DCPF solve ---
Converged: True, wall clock: 0.223s
DCPF flows range: [-1839.578, 2035.364]

--- LinearAnalysis ---
PTDF compute time: 15.494s
PTDF shape: (12706, 10000), range: [-2.339, 1.790]

--- LA direct flows vs DCPF ---
Max abs diff:  743.4624 MW
Mean abs diff:   2.6797 MW
Median abs diff: 0.1303 MW
90th pctile:     4.1068 MW
99th pctile:    43.6389 MW
Branches > 1 MW diff:   3007
Branches > 10 MW diff:   575
Branches > 100 MW diff:   53

Top 3 worst branches:
  [11244] Xfmr '28737_28745_1': LA=1291.9, DCPF=2035.4, diff=743.5
  [7276]  Line '50203_50059_1': LA=101.1,   DCPF=-461.8, diff=562.9
  [11955] Xfmr '50203_50207_1': LA=-101.1,  DCPF=461.8,  diff=562.9

--- Divergence by branch type ---
Lines (9726):        max=562.87, mean=2.75
Transformers (2980): max=743.46, mean=2.46

--- PTDF @ Sbus vs DCPF ---
Max abs diff: 15139.36 MW
Mean abs diff:   29.57 MW

--- Root cause investigation ---
Islands: 1 (single island; NOT the cause)
Non-unity tap transformers: 970 / 2980
Tap deviation vs error correlation: -0.03 (no correlation; taps NOT the cause)
Slack bus: Bus 7236 'PHOENIX 74 6', injection=-1119.5 MW
Zeroing slack injection did not improve PTDF@Sbus match

Total probe wall clock: 22.71s
```

## Analysis

The probe reproduces the original claim's numbers with exact precision:
- LA vs DCPF max diff: 743.46 MW (original: 743.46 MW)
- PTDF @ Sbus vs DCPF max diff: 15,139.36 MW (original: 15,139.36 MW)
- Mean diffs and other statistics also match precisely

Root cause investigation:
- **Island handling**: Ruled out. The network has a single island.
- **Transformer tap effects**: Ruled out. Correlation between tap deviation and flow error is -0.03 (essentially zero). Both lines and transformers show large errors, and the mean error is actually slightly lower for transformers.
- **Slack bus treatment**: The PTDF correctly zeroes out the slack bus column (bus 7236). Zeroing the slack injection in Sbus before computing PTDF@Sbus did not help.
- **Most likely cause**: The LinearAnalysis and DCPF solvers use different internal formulations or admittance matrix constructions on large networks. The worst mismatches cluster around specific subnetwork regions (buses 28xxx, 50xxx), suggesting localized numerical differences in how the two solvers build and factor the susceptance matrix. The divergence grows with network complexity -- the original evaluation noted exact match on the 39-bus network.

The qualified_pass scoring is reasonable: the PTDF matrix is accessible, correctly dimensioned, and usable for sensitivity analysis, but its absolute flow predictions diverge from the DCPF solver on this large network.

## Classification Rationale

Classified as **claim_supported** because:
1. The probe reproduced the exact max diff values (743.46 MW and 15,139.36 MW) on the same version (5.6.28)
2. The qualified_pass scoring rationale (PTDF accessible but flow predictions diverge) is confirmed
3. Root cause investigation confirms the divergence is real and not due to trivial causes (islands or tap ratios)
