---
tag: workaround-needed
source_dimension: extensibility
source_test: B-1
tool: gridcal
severity: high
timestamp: "2026-03-24T00:00:00Z"
---

# Observation: Fragile monkey-patch workaround required for custom OPF constraints

## Finding

Adding a flowgate constraint to GridCal's DC OPF required monkey-patching `PulpLpModel.solve` and accessing internal constraint naming conventions. This is classified as a fragile workaround that could break on any version update.

## Context

During B-1, the constraint injection workaround depends on three undocumented internals: (1) internal constraint naming `br_flow_upper_lim_0_<idx>`, (2) the `PulpLpModel` class in `VeraGridEngine.Utils.MIP.pulp_interface`, (3) slack variable naming `flow_slack_pos_0_<idx>`. Despite being fragile, the workaround successfully demonstrates that dual values are extractable and correctly reflect binding/non-binding status. The binding case dual = -60.1 $/MWh; the non-binding case dual = 0.

## Implications

The fragile workaround classification limits B-1 to `partial_pass` under the v11 five-tier outcome system. This is a tool-specific limitation [tool-specific: no custom constraint API], not a solver limitation.
