---
tag: workaround-needed
source_dimension: extensibility
source_test: B-8
tool: pandapower
severity: low
timestamp: "2026-03-13T00:00:00Z"
---

# Observation: Slack bus reconfiguration uses stable workaround (public API only)

## Finding

Changing the slack/reference bus in pandapower requires a multi-step workaround involving element removal and recreation. The workaround uses only documented public API (create_ext_grid, create_gen, create_poly_cost, DataFrame.drop) and is classified as stable. However, the verbosity (5-6 calls) and the need to manually transfer cost functions between element types makes the process error-prone.

## Context

During B-8 testing, three slack configurations were successfully tested. All converged and produced consistent, different LMP patterns. The workaround is durable but adds friction compared to tools that treat the slack designation as a simple bus-level attribute.

## Implications

The workaround classification is stable (public API, will not break on upgrade), but the API friction should be noted in the extensibility grade assessment. This is a design limitation, not a missing feature -- pandapower's ext_grid concept is well-documented and intentional, but it makes reference bus reconfiguration unnecessarily complex.
