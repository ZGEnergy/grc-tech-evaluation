---
tag: api-friction
source_dimension: fnm_ingestion
source_test: G-FNM-1
tool: pypsa
severity: high
timestamp: 2026-03-24T12:00:00Z
---

# Observation: PyPSA has no PSS/E or intermediate CSV ingestion path

## Finding

PyPSA v1.1.2 cannot ingest PSS/E-format network data in any form -- neither native
`.raw` files nor the intermediate CSV tables derived from PSS/E v31 record types.
This is a blocking API gap for any workflow that starts from PSS/E data.

## Context

During G-FNM-1 (intermediate format ingestion), all six PyPSA import methods were
inspected. The tool supports its own CSV format, PYPOWER PPC dicts, pandapower
networks, HDF5, NetCDF, and Excel -- but none of these accept PSS/E field names,
record type structures, or the 17-table intermediate schema. Loading PSS/E data
into PyPSA requires an external conversion step (e.g., via MATPOWER `.m` files and
`import_from_pypower_ppc`, or via pandapower's PSS/E reader and
`import_from_pandapower_net`).

## Implications

This finding is relevant to the Accessibility dimension. Users working with PSS/E
data (the dominant format in North American ISOs) face a mandatory format conversion
step before they can use PyPSA. The MATPOWER `.m` fallback path loses PSS/E-specific
fields (FACTS, switched shunts, multi-terminal DC, transformer control modes) that
cannot be represented in the MATPOWER format. The pandapower bridge path preserves
more fields but introduces a dependency on pandapower as a data conversion layer.
