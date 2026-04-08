---
tag: api-friction
source_dimension: fnm_ingestion
source_test: G-FNM-1
tool: powermodels
severity: high
timestamp: "2026-03-24T00:00:00Z"
---

# Observation: PSS/E intermediate CSV format not supported (blocking)

## Finding

PowerModels.jl has no CSV ingestion path. The tool supports only MATPOWER `.m`, PSS/E
`.raw` (v33), and PowerModels JSON formats. The intermediate CSV tables derived from
PSS/E cannot be loaded, requiring an external MATPOWER `.m` conversion as a prerequisite
for any FNM analysis.

## Context

G-FNM-1 tests whether the tool can ingest the intermediate CSV format (17 tables derived
from PSS/E v31 records). PowerModels' `parse_file()` dispatches on file extension and
does not recognize `.csv`. Additionally, its PSS/E RAW parser fails on the FNM's v31
header format due to a single-line Case Identification parsing limitation.

The MATPOWER fallback path works (3.05s load time, ~28,000 buses), but the fallback file
is a pre-cleaned main-island subset with fewer records than the raw source (bus count
deficit: -8.1%, load count deficit: -42.7%).

## Implications

This is a blocking limitation for FNM ingestion capability. The tool cannot consume the
authoritative intermediate format and depends on an external conversion step. This should
be noted in accessibility assessment (D-suite) as a significant onboarding barrier for
users working with PSS/E-derived network models. The limitation is tool-specific (not
solver-related) and architectural -- adding CSV support would require new parser code.
