---
tag: fnm-data-model
source_dimension: fnm_ingestion
source_test: G-FNM-5
tool: pandapower
severity: high
timestamp: 2026-03-24T12:00:00Z
---

# Observation: pandapower lacks interface/flowgate and contingency definition data models

## Finding

pandapower has no native data model for transmission interfaces (flowgates) or
contingency definitions. INTERFACE.csv is 100% tool-external (5/5 fields), and
CONTINGENCY.csv has 2 of 6 fields tool-external (CONTINGENCY_NAME, ELEMENT_TYPE).
This means 43% of all supplemental CSV fields (19/44) must be maintained outside
pandapower's network model.

## Context

G-FNM-5 classified all 44 supplemental CSV fields for pandapower and found that
the tool's DataFrame-based data model accommodates physical network elements
(buses, lines, generators) well via native fields and custom columns, but has no
structural analog for market-layer concepts (trading hubs, generator distribution
factors) or reliability analysis concepts (interfaces, contingency definitions,
outage schedules). The interface gap is particularly consequential because
interface flow limits cannot be enforced within pandapower's OPF formulation --
they require either external post-processing or the PandaModels.jl Julia bridge.

## Implications

This finding directly impacts the Extensibility dimension: pandapower's extension
mechanism (custom DataFrame columns) is stable and well-documented for carrying
metadata, but it cannot make the tool's solver aware of interface constraints or
contingency definitions. The 43% external rate indicates that nearly half of
FNM supplemental data requires parallel data structures, increasing integration
complexity for Phase 2 congestion analysis workflows. The contingency definition
gap is partially mitigated by `run_contingency()` accepting element indices, but
the absence of named contingency objects means contingency management logic must
be built externally.
