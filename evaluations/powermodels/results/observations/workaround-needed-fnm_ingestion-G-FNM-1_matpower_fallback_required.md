---
tag: workaround-needed
source_dimension: fnm_ingestion
source_test: G-FNM-1
tool: powermodels
severity: high
timestamp: "2026-03-13T00:00:00Z"
---

# Observation: MATPOWER Fallback Required for FNM Ingestion

## Finding

PowerModels cannot ingest the FNM intermediate CSV format or the source PSS/E v31 RAW file.
The only viable ingestion path is a pre-converted MATPOWER `.m` fallback file, which
requires an external conversion step and produces a cleaned derivative with fewer records
than the raw source.

## Context

G-FNM-1 tested three ingestion paths:
1. Intermediate CSV: No CSV parser in PowerModels (not attempted)
2. PSS/E v31 RAW: Parser fails on Case Identification header format
3. MATPOWER `.m` fallback: Loads successfully (2.97 s, 27,862 buses)

The workaround classification is `blocking` because the external conversion step
(MATPOWER/Octave `psse2mpc()` or equivalent) is outside PowerModels' control and
produces a lossy derivative (isolated buses, loads, and branches are dropped).

## Implications

This workaround is relevant to the Extensibility dimension -- PowerModels' data ingestion
pipeline requires an external MATPOWER conversion step for real-world ISO network models.
Any analyst workflow using PowerModels for FNM-based analysis must include a separate
format conversion stage, adding operational complexity and introducing a potential source
of data loss.
