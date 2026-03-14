---
tag: api-friction
source_dimension: fnm_ingestion
source_test: G-FNM-1
tool: matpower
severity: high
timestamp: "2026-03-13T00:00:00Z"
---

# Observation: MATPOWER cannot ingest intermediate CSV tables

## Finding

MATPOWER has no built-in capability to import the intermediate CSV format (17 tables
representing PSS/E v31 record types). Its data ingestion API is limited to MATPOWER
case files (`.m`/`.mat` via `loadcase()`) and PSS/E RAW files (via `psse2mpc()`).
Building a CSV-to-MPC importer would require hundreds of lines of custom Octave code,
equivalent in scope to the existing `psse2mpc()` function.

## Context

G-FNM-1 sub-check (a) tested whether MATPOWER can parse intermediate CSV tables
containing PSS/E v31 records (bus, load, generator, branch, transformer, etc.). The
MATPOWER 8.1 function library was surveyed for any CSV import function (`csv2mpc`,
`importcsv`, `load_csv`, `readcsv`) -- none exist. The tool's data model is tightly
coupled to its own case format, where bus/branch/gen data are stored as numeric
matrices with positional column semantics rather than named fields.

This is a fundamental architectural limitation: MATPOWER's MPC struct uses
position-indexed numeric matrices (e.g., column 1 of the bus matrix is bus number,
column 2 is bus type), while the intermediate CSV format uses named columns with
string and numeric types. Bridging these representations requires explicit field
mapping logic for each of the 17 record types.

## Implications

This finding is relevant to the Accessibility audit (D-2, D-4): MATPOWER's data
ingestion flexibility is limited compared to tools with general-purpose DataFrame
APIs. Any workflow requiring data from non-MATPOWER sources must either pre-convert
to `.m`/`.mat` format or build custom import code. This increases integration effort
for operational use cases where network data arrives in tabular or PSS/E-adjacent
formats that are not exact RAW files.

G-FNM-3, G-FNM-4, and G-FNM-5 proceed via the MATPOWER fallback path
(`data/fnm/reference/cleaned/fnm_main_island.mat`), which provides the FNM network
in MATPOWER's native format.
