---
tag: fnm-data-model
source_dimension: fnm_ingestion
source_test: G-FNM-5
tool: matpower
severity: medium
timestamp: "2026-03-24T18:00:00Z"
---

# Observation: MATPOWER has native interface support but lacks contingency and market-layer models

## Finding

MATPOWER achieves 45% native field coverage across the 7 supplemental CSVs
(20 of 44 fields), ranking second among all six evaluated tools. Its native
`mpc.if`/`mpc.iflim` interface support is a differentiator shared only with
PowerSimulations.jl. However, MATPOWER lacks native contingency definitions,
trading hub models, and outage scheduling -- requiring external data
structures for these market-critical concepts.

## Context

G-FNM-5 classified each of the 44 fields across 7 supplemental CSVs as
Native (N), Extension (E), or External (X) for MATPOWER. Key strengths:
3-tier thermal ratings (RATE_A/B/C), interface definitions and flow limits
(`mpc.if`/`mpc.iflim`). Key gaps: no contingency object (must script
BR_STATUS toggling), no generator name field (extension only), no temporal
or market-layer concepts.

The extension mechanism (arbitrary `mpc` struct fields) provides a clean
path for carrying 27% of fields (12/44) alongside the network model without
external data structures.

## Implications

For expressiveness assessment: MATPOWER's interface support (`mpc.if`)
enables native SCOPF with interface flow constraints, which is relevant
for tests A-9 and B-1 (custom constraints including flowgate limits).
The lack of contingency definitions means N-1/N-2 analysis (B-3) requires
scripted branch status modification rather than declarative contingency
specifications.

For Phase 2 congestion analysis readiness: MATPOWER's native interface
support positions it well for flowgate-based congestion management.
However, the absence of trading hub definitions and generator distribution
factors means hub-level price computation must be handled entirely
externally.
