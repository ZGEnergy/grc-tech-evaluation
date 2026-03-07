---
tag: arch-quality
source_dimension: extensibility
source_test: B-6
tool: pandapower
severity: low
timestamp: 2026-03-06T00:00:00Z
---

# Observation: Clean 4-layer architecture with informal interfaces

## Finding

pandapower's DCPF solve path traverses 4 well-separated abstraction layers (API -> orchestration -> data conversion -> solver), spanning 361 Python files and ~89K LOC. However, layer boundaries are enforced by convention, not by formal interface contracts (no abstract base classes or protocols between layers).

## Context

Traced during B-6 code architecture audit. The two-layer design (user-facing pandas DataFrames converted to MATPOWER numpy arrays for computation) is clean and well-established. The conversion pipeline (`_pd2ppc`) is a large monolithic function (~900 lines) but serves its purpose.

## Implications

The informal interfaces mean that deep extensions (custom elements, custom formulations) require understanding undocumented internal structures. This is relevant for the maturity assessment -- the architecture is pragmatic and functional but not formally modular in the software engineering sense. The controller framework provides the primary sanctioned extension point.
