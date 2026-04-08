---
tag: api-friction
source_dimension: fnm_ingestion
source_test: G-FNM-1
tool: gridcal
severity: high
timestamp: 2026-03-24T00:00:00Z
---

# Observation: No CSV network import and silent .mat failure

## Finding

GridCal/VeraGrid v5.6.28 cannot ingest the intermediate CSV tables (PSS/E v31
record data in CSV form) because it has no CSV-to-network import path.
Additionally, `open_file()` silently returns `None` for MATLAB `.mat` binary
files rather than raising an informative error, creating a silent failure mode.

## Context

During G-FNM-1 (intermediate format ingestion gate), GridCal was tested for its
ability to parse 17 intermediate CSV tables derived from a PSS/E v31 RAW file.
GridCal has no native CSV import for network topology data -- its `open_file()` API
accepts `.raw`, `.rawx`, `.m`, `.veragrid`, `.xlsx`, `.json`, and various XML-based
formats, but not CSV tables representing network elements.

When the MATPOWER fallback was tested, the `.mat` binary format (MATLAB native)
returned `None` from `open_file()` without raising an exception. Subsequent
attribute access on the result (`grid.buses`) raises `AttributeError`. Only the
`.m` text format works correctly, loading the ~28,000-bus main-island case.

The MATPOWER `.m` fallback path works successfully for downstream G-FNM-3/4/5
tests but cannot support G-FNM-1 (CSV ingestion) or G-FNM-2 (field coverage
audit) because the `.m` format loses PSS/E-specific fields.

## Implications

- **Accessibility (D dimension):** The absence of CSV import for network data is
  a significant API friction point. Users working with standardized PSS/E data
  in CSV form have no import path. The silent `None` return for `.mat` files
  (rather than an informative error) compounds the friction.

- **Extensibility (B dimension):** Building a custom CSV-to-GridCal adapter would
  require mapping all 17 PSS/E record types to GridCal's object model (Bus, Line,
  Transformer2W, Generator, Load, Shunt, etc.) with correct attribute mapping.

- **Maturity (E dimension):** Silent failure modes (returning `None` instead of
  raising an exception for unsupported formats) indicate incomplete error handling
  in the file I/O layer.
