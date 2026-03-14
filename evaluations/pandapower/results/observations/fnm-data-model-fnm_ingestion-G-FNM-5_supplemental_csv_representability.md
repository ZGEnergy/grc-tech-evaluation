---
tag: fnm-data-model
source_dimension: fnm_ingestion
source_test: G-FNM-5
tool: pandapower
severity: medium
timestamp: 2026-03-13T12:00:00Z
---

# Observation: pandapower lacks native market-layer data structures

## Finding

pandapower has no native representation for trading hubs, generator
distribution factors, contingency definitions, or transmission
interfaces. 43% of supplemental CSV fields (19 of 44) are classified
as tool-external (X), requiring parallel data structures maintained
outside pandapower's network model.

## Context

G-FNM-5 assessed pandapower's ability to carry 7 supplemental CSV
datasets within its network model. pandapower achieves 34% native
(N), 23% extension (E), and 43% external (X) field coverage. The
X-classified fields are concentrated in market-layer concepts (trading
hubs: 75% X, interfaces: 100% X) and temporal concepts (outage
schedules: 50% X). Extension-classified fields use custom DataFrame
columns, which are preserved through serialization but not consumed
by any analysis function.

## Implications

For the expressiveness dimension, pandapower's market-layer gaps mean
that congestion analysis workflows requiring interface flow limits or
hub-level LMP computation will involve significant external data
management. For the extensibility dimension, the custom DataFrame
column mechanism provides a clean extension path for carrying
supplemental data, but the data remains semantically inert — custom
code is required for every use case beyond storage.
