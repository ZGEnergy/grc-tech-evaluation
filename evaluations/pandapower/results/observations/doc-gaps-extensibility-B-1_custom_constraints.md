---
tag: doc-gaps
source_dimension: extensibility
source_test: B-1
tool: pandapower
severity: medium
timestamp: "2026-03-13T00:00:00Z"
---

# Observation: PYPOWER userfcn mechanism undocumented in pandapower

## Finding

pandapower inherits the PYPOWER `userfcn` callback system for OPF extensibility (supporting 5 callback stages: ext2int, formulation, int2ext, printpf, savecase). This mechanism is used internally by pandapower for dcline constraints but is not documented in pandapower's own documentation. Users must read PYPOWER source code to discover and use it.

## Context

During B-1 testing, the userfcn mechanism was discovered by inspecting `pandapower/optimal_powerflow.py` source code (line 28: `ppci = add_userfcn(ppci, 'formulation', _add_dcline_constraints, args=net)`). The PYPOWER source in `pandapower/pypower/add_userfcn.py` contains thorough docstrings explaining the callback stages, but pandapower's official documentation makes no mention of this extension point.

## Implications

This is relevant to the Accessibility audit. The gap between pandapower's documentation (which describes only predefined OPF constraints via element DataFrame columns) and the actual capability (arbitrary linear constraints via userfcn) is significant. Users looking for custom constraint support in the documentation would conclude it is not possible, when in fact the infrastructure exists.
