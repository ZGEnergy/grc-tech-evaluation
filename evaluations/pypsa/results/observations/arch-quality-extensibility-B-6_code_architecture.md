---
tag: arch-quality
source_dimension: extensibility
source_test: B-6
tool: pypsa
severity: low
timestamp: 2026-03-11T00:00:00Z
---

# Observation: Strong OPF extensibility; DCPF solver is hard-coded

## Finding

PyPSA has a well-architected OPF pipeline with clean model-build/solve separation and a documented injection point (`extra_functionality`). The DCPF pipeline uses scipy.sparse directly and has no solver swap mechanism — a contrast with the OPF's linopy-based solver abstraction.

## Context

B-6 architecture assessment traced the call chain from `n.lpf()` through the 8-mixin `Network` class to `SubNetwork` and finally to `scipy.sparse.linalg`. The OPF accessor (`n.optimize`) exposes `create_model()` / `solve_model()` as separate steps and allows full access to the linopy model before solve. The DCPF solver is `scipy.sparse` with no configurability.

The mixin architecture (8 mixins: NetworkComponentsMixin, NetworkDescriptorsMixin, NetworkTransformMixin, NetworkIndexMixin, NetworkConsistencyMixin, NetworkGraphMixin, NetworkPowerFlowMixin, NetworkIOMixin) provides good separation of concerns but creates a non-obvious method resolution order that makes it hard to find where a given method is defined without reading the full method resolution order.

## Implications

Positive for Maturity (D-tests): the OPF architecture shows design investment in extensibility. The `extra_functionality` pattern is idiomatic and would score well in a design quality assessment.

Negative for Extensibility grading: the lack of a solver-swap mechanism for DCPF (contrast with OPF) means that some extensibility scenarios — e.g., plugging in a custom DC solver — require monkey-patching. For the OPF path this is not an issue.
