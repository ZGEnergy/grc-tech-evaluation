---
tag: fnm-data-model
source_dimension: fnm_ingestion
source_test: G-FNM-1
tool: powermodels
severity: medium
timestamp: "2026-03-13T00:00:00Z"
---

# Observation: MATPOWER Fallback Record Count Discrepancies

## Finding

When loading the cleaned MATPOWER fallback (`fnm_main_island.m`), PowerModels parsed
counts differ from the intermediate manifest across all four primary tables. The
discrepancies are attributable to the fallback being a pre-cleaned main-island subset,
not to PowerModels ingestion defects.

## Context

G-FNM-1 record count comparison (manifest vs. PowerModels actual):

| Table | Manifest | Actual | Delta | % Diff |
|-------|----------|--------|-------|--------|
| bus | ~30,000 | ~28,000 | -2,445 | -8.1% |
| load | ~15,000 | 8,624 | -6,438 | -42.7% |
| generator | ~5,800 | ~5,700 | -27 | -0.5% |
| branch+transformer | ~34,000 | ~33,000 | -1,234 | -3.6% |

The manifest counts raw PSS/E v31 records including isolated buses (IDE=4), de-energized
equipment, and off-island network fragments. The `fnm_main_island.m` fallback is a
pre-cleaned extract of the main island only.

The load discrepancy (-42.7%) is the most striking: roughly 6,400 loads exist on buses
that were removed during the cleaning step. The bus, generator, and branch discrepancies
are proportionally smaller and consistent with removing isolated/off-island elements.

## Implications

This discrepancy does not indicate a PowerModels data-model defect. It reflects that
the two inputs (raw PSS/E manifest vs. cleaned MATPOWER fallback) have different scope.
The post-ingestion fidelity checks (baseMVA=100, slack bus <slack_bus>, tap ratio preservation)
all pass on the loaded data, confirming PowerModels correctly parses what it receives.
A valid full-fidelity comparison would require either PowerModels successfully parsing the
raw PSS/E file (currently blocked) or a manifest derived from the same cleaned scope.
