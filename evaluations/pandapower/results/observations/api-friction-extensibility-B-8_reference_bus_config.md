---
tag: api-friction
source_dimension: extensibility
source_test: B-8
tool: pandapower
severity: medium
timestamp: "2026-03-13T00:00:00Z"
---

# Observation: Changing slack bus requires 5-6 API calls with element-type juggling

## Finding

pandapower has no `set_slack_bus()` or `set_reference_bus()` API. The slack bus is architecturally tied to the `ext_grid` element type. Changing the reference bus requires removing the old `ext_grid`, creating a `gen` in its place, removing any `gen` at the new slack bus, creating a new `ext_grid` there, and manually transferring cost functions between element types -- a total of 5-6 API calls with careful index management.

## Context

During B-8 (reference bus configuration), three different slack configurations were tested. Each reconfiguration required: (1) removing old ext_grid + its poly_cost, (2) creating gen at old slack bus + new poly_cost, (3) removing gen at new slack bus + its poly_cost, (4) creating ext_grid at new bus + new poly_cost. The process uses only public API but is error-prone because cost functions are tied to specific element indices and element types.

## Implications

This friction pattern is relevant for the Accessibility audit: users performing sensitivity analysis on reference bus placement face a multi-step, error-prone process. The ext_grid/gen distinction is fundamental to pandapower's architecture and unlikely to change, so this friction is permanent. Tools that decouple the "slack" property from the element type (e.g., via a bus-level attribute) would score higher on this dimension.
