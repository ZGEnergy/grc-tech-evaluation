---
tag: fnm-scale
source_dimension: fnm_ingestion
source_test: G-FNM-3
tool: pandapower
severity: low
timestamp: 2026-03-14T04:00:00Z
---

# Observation: pandapower DCPF solves ~28,000-bus FNM in 0.40 seconds

## Finding

pandapower's `rundcpp()` solved the ~28,000-bus FNM main island DCPF in 0.40 seconds
wall-clock time. Network loading via `matpowercaseframes` + `from_ppc` took an
additional 0.18 seconds. Total ingestion-to-solution time was under 2 seconds.

## Context

G-FNM-3 loaded the pre-cleaned FNM main island (~28,000 buses, ~33,000 branches,
~5,700 generators) and ran DCPF. Despite the test failing due to a hard-fail
condition on localized branch flow outliers, the solver itself performed well:
the DCPF converged immediately and produced results matching the reference
solution on 99.64% of buses and 99.67% of branches.

## Implications

The 0.40-second solve time on a ~28K bus network demonstrates pandapower's
scalability for DCPF is adequate for the LARGE tier. This finding is relevant
to the scalability dimension's assessment of pandapower's performance at scale.
