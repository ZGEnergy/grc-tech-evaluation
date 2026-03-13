# Observation: fnm-data-model — MATPOWER Fallback Record Count Discrepancies

**observation_type:** fnm-data-model
**test_id:** G-FNM-1
**dimension:** fnm_ingestion
**tool:** powermodels
**severity:** informational (fallback scope mismatch; not a PowerModels defect)
**timestamp:** 2026-03-11T00:00:00Z

## Finding

When loading the cleaned MATPOWER fallback (`fnm_main_island.m`), PowerModels parsed counts
differ from the intermediate manifest across all four primary tables:

| Table              | Manifest | Actual | Delta  | %     |
|--------------------|----------|--------|--------|-------|
| bus                | 30307    | 27862  | −2445  | −8.1% |
| load               | 15062    | 8624   | −6438  | −42.7%|
| generator          | 5768     | 5741   | −27    | −0.5% |
| branch+transformer | 33840    | 32606  | −1234  | −3.6% |

## Interpretation

The manifest counts raw PSS/E v31 records including isolated buses (`bus_type=4`),
de-energized equipment, and off-island network fragments. The `fnm_main_island.m`
fallback file is a pre-cleaned extract of the main island only — it intentionally
excludes those elements.

The load discrepancy (−42.7%) is the most striking: roughly 6,400 loads exist on
buses that were removed during the cleaning step or are attached to the off-network
model. This reflects that a large portion of the PSS/E load records are on off-island
or isolated buses.

## Implications for Tool Evaluation

This discrepancy does not indicate a PowerModels data-model defect. It reflects that
the two inputs (raw PSS/E manifest vs. cleaned MATPOWER fallback) have different scope.
A valid G-FNM-1 test would require either:

1. PowerModels successfully parsing the raw PSS/E file (currently blocked), or
2. A MATPOWER fallback whose manifest counts were derived from the same cleaned scope.

If G-FNM-1 were run against the raw PSS/E file successfully, the branch+transformer
merged count check (33840) would be the key verification for PowerModels' transformer
merge accounting.
