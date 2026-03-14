---
tag: workaround-needed
source_dimension: fnm_ingestion
source_test: G-FNM-3
tool: pandapower
severity: medium
timestamp: 2026-03-14T04:00:00Z
---

# Observation: MATPOWER fallback required for FNM DCPF verification

## Finding

pandapower requires MATPOWER fallback for FNM ingestion because it has no native
CSV import capability. The DCPF verification used `matpowercaseframes.CaseFrames`
to parse the cleaned `.m` file followed by `from_ppc` conversion. This is the same
stable workaround documented in G-FNM-1. Additionally, the `from_ppc` zero-RATE_A
bug workaround was applied.

## Context

G-FNM-3 needed to load the pre-cleaned FNM main island for DCPF comparison against
the reference solution. The tool cannot ingest intermediate CSV files directly, so
the `input_path: matpower` fallback was used. Both workarounds are classified as
stable (documented public APIs, deterministic pre-processing).

## Implications

The MATPOWER fallback is a persistent limitation for the FNM evaluation pipeline.
Any tool evaluation involving CSV-formatted network data requires an external
conversion step for pandapower. This is relevant to the extensibility dimension's
assessment of pandapower's data interoperability.
