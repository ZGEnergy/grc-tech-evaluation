---
tag: api-friction
source_dimension: fnm_ingestion
source_test: G-FNM-1
tool: gridcal
severity: high
timestamp: 2026-03-13T00:00:00Z
---

# Observation: No CSV network import and PSS/e v31 RAW parsing failure

## Finding

GridCal/VeraGrid v5.6.28 cannot ingest the intermediate CSV tables (PSS/e v31
record data in CSV form) because it has no CSV-to-network import path. Additionally,
GridCal's PSS/e RAW parser fails on v31 format files, expecting v35 format instead.

## Context

During G-FNM-1 (intermediate format ingestion gate), GridCal was tested for its
ability to parse 17 intermediate CSV tables derived from a PSS/e v31 RAW file.
GridCal has no native CSV import for network topology data -- its `open_file()` API
accepts `.raw`, `.rawx`, `.m`, `.veragrid`, `.xlsx`, `.json`, and various XML-based
formats, but not CSV tables representing network elements.

When the source PSS/e RAW file (v31) was tested directly, GridCal's parser failed
with: `PSSe 35 load data came with 1 elements and 18 or 17 were expected`. This
indicates the parser is hardcoded for PSS/e v35 format and cannot handle v31
differences in record structure (e.g., different column counts in the load section).

The MATPOWER `.m` fallback path works successfully, loading the cleaned main-island
case (27,862 buses). This path is available for downstream G-FNM-3/4/5 tests.

## Implications

- **Accessibility (D dimension):** The absence of CSV import for network data and
  the inability to parse PSS/e v31 (only v35) are significant API friction points
  for users working with legacy or standards-based data formats. ISO/RTO data
  (including large-scale FNM data) is commonly distributed in PSS/e v31 format.

- **Extensibility (B dimension):** Building a custom CSV-to-GridCal adapter would
  require mapping all 17 PSS/e record types to GridCal's object model (Bus, Line,
  Transformer2W, Generator, Load, Shunt, etc.) with correct attribute mapping. This
  is feasible but represents significant development effort.

- **Maturity (E dimension):** PSS/e v31 is the most widely used version in North
  American utility practice. A power system tool that only supports v35 has a
  compatibility gap with the installed base of network models.
