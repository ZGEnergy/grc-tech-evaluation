---
tag: api-friction
source_dimension: fnm_ingestion
source_test: G-FNM-1
tool: pandapower
severity: high
timestamp: 2026-03-24T12:00:00Z
---

# Observation: pandapower lacks any PSS/E format parser, blocking intermediate CSV ingestion

## Finding

pandapower 3.4.0 has no PSS/E format parser of any kind -- neither RAW file
parsing nor CSV record-type import. The tool's import paths are limited to
MATPOWER .m/.mat (via `from_mpc`/`from_ppc`) and pandapower's own JSON/pickle
serialization. This is a blocking gap for the intermediate CSV ingestion pathway.

## Context

During G-FNM-1 testing, a scan of pandapower's public API (`pandapower` and
`pandapower.converter` modules) found no function capable of parsing PSS/E v31
record-type CSV tables. The only API with a superficially similar name was
`get_raw_data_from_pickle`, which loads pandapower's own pickle format, not
PSS/E RAW data. The 17-table intermediate CSV format (bus, load, generator,
branch, transformer, etc.) derived from PSS/E v31 records cannot be consumed
by any pandapower function.

The tool can still load the FNM via a MATPOWER .mat fallback path (demonstrated
in the v10 evaluation), but this path loses field granularity: per-load records
are aggregated to bus level, transformer-specific PSS/E fields (83 columns) are
collapsed to the MATPOWER branch matrix format, and switched shunt control
parameters are lost.

## Implications

- **Accessibility dimension:** The absence of PSS/E parsing means users working
  with ISO-provided RAW files (the standard exchange format for North American
  ISOs) must pre-convert to MATPOWER format using external tools before loading
  into pandapower. This adds a mandatory preprocessing step to any workflow
  starting from PSS/E data.
- **Extensibility dimension:** The MATPOWER fallback path loses PSS/E-specific
  fields that have no MATPOWER equivalent (e.g., switched shunt discrete steps,
  transformer tap control modes, area interchange parameters). Tools that can
  ingest intermediate CSVs directly will have richer data models for downstream
  analysis.
- **G-FNM-2 blocked:** The field coverage audit cannot be performed on the
  intermediate ingestion path because no network model is produced.
