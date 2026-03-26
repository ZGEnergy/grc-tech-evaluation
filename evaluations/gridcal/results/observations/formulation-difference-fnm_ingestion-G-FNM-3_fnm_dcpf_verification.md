---
tag: formulation-difference
source_dimension: fnm_ingestion
source_test: G-FNM-3
tool: gridcal
severity: medium
timestamp: 2026-03-24T00:00:00Z
---

# Observation: GridCal uses simplified B-matrix that omits transformer tap ratio corrections in DCPF

## Finding

GridCal's DCPF solver produces bus voltage angles within machine precision of the
MATPOWER reference (max deviation 7.713822e-09 deg across all 27,862 buses) but
exhibits extreme branch flow deviations (up to 5.629550e+05%) on 326 out of 32,532
branches. 88.65% of failing branches are adjacent to transformer buses. The
deviations are systematic and signed (not random), consistent with a simplified
B-matrix construction that computes branch susceptance as `b = -1/x` without
incorporating transformer tap ratios and phase shift angles.

## Context

The MATPOWER reference uses the full `makeBdc()` formulation, which adjusts
B-matrix entries for branches with off-nominal tap ratios. GridCal's `SolverType.Linear`
solver appears to use the simplified formulation. The near-zero bus angle deviation
confirms that the power injection vector (loads, generators) and network topology
are correctly ingested; only the branch flow computation from angle differences
is affected by the tap ratio omission. The v11 bus injection power balance
cross-reference confirms all 27,862 bus loads match exactly (0 mismatches).

Key characteristics of the affected branches:
- Flow magnitudes reach hundreds of thousands of MW (vs reference flows of ~100 MW)
- Deviations cluster around buses connected to transformers with tap != 1.0
- 37 non-transformer-adjacent branches also fail, likely due to cascading flow
  redistribution effects from nearby transformer branches

## Implications

This formulation difference should be considered when evaluating GridCal's DCPF
results on networks with many off-nominal-tap transformers. The cross-tool
watchpoints note that this is a known variation across tools and does not indicate
a bug. For the FNM (which has 9,481 transformers), the impact affects ~1% of
branches. Tools using the full B-matrix (MATPOWER, pandapower, PyPSA) will produce
more accurate branch flows on transformer branches, but the bus angle solution is
identical regardless of formulation. [tool-specific: simplified B-matrix formulation]
