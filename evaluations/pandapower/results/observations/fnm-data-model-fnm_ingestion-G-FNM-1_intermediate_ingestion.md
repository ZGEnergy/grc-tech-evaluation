---
tag: fnm-data-model
source_dimension: fnm_ingestion
source_test: G-FNM-1
tool: pandapower
severity: medium
timestamp: 2026-03-14T03:00:00Z
---

# Observation: pandapower data model diverges from intermediate format on load and branch classification

## Finding

pandapower's PPC import path aggregates multiple loads per bus into a single load
element (8,576 vs ~15,000 expected) and classifies branches by voltage level rather
than tap ratio, splitting the ~34,000 MATPOWER branch records into 24,165 lines +
2,393 trafos + 7,282 impedances instead of the intermediate format's ~24,000
branches + ~9,700 transformers. Additionally, 55 extra sgen elements are created
from buses with negative active power demand.

## Context

During G-FNM-1 ingestion testing, pandapower loaded the ~30,000-bus FNM network
via `from_ppc()`. The merged branch total (~34,000) and bus count (~30,000) match
exactly. However, the per-table record counts diverge from the intermediate
manifest because pandapower uses a fundamentally different element classification
scheme. The load aggregation means that per-load attributes (individual load ID,
status, area, zone) from the PSS/E load records are lost in the MATPOWER/PPC
import path.

## Implications

The load aggregation and branch reclassification do not affect power flow accuracy
(total bus injection is preserved), but they reduce data fidelity for downstream
analyses that depend on individual load records (e.g., load distribution factors,
per-load sensitivity analysis). Tools that ingest intermediate CSVs directly
and preserve per-load granularity will have a data model advantage for market
solution workflows.
