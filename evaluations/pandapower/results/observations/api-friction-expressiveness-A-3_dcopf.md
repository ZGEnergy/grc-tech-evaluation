---
tag: api-friction
source_dimension: expressiveness
source_test: A-3
tool: pandapower
severity: low
timestamp: "2026-03-13T00:00:00Z"
---

# Observation: Bus number indexing mismatch with MATPOWER data

## Finding

pandapower's `from_mpc` converter remaps MATPOWER 1-indexed bus numbers to 0-indexed pandas DataFrame indices. When loading external CSV data that references MATPOWER bus numbers (e.g., gen_temporal_params.csv with bus_id 30-39), users must subtract 1 to match pandapower indexing (buses 29-38). There is no explicit documentation of this mapping.

## Context

During A-3 (DC OPF with Modified Tiny data), the initial implementation used raw bus_id values from the CSV, causing a lookup failure for bus 39 (which is pandapower bus 38). The fix was a simple `bus_id - 1` offset, but this is an easy source of errors when integrating external data.

## Implications

For accessibility (D-2 documentation): The 0-indexed bus mapping is not prominently documented in the converter documentation. Users importing MATPOWER cases and cross-referencing with external data sources need to be aware of this indexing shift.
