---
tag: doc-gaps
source_dimension: extensibility
source_test: B-1
tool: pypsa
severity: low
timestamp: 2026-03-11T00:00:00Z
---

# Observation: Line flow variable renamed from `Line-p` to `Line-s` in v1.1.2

## Finding

In PyPSA v1.1.2, the linopy variable for line flow is named `Line-s` (apparent power), not `Line-p` (active power) as documented in older tutorials and the pre-v1.0 API. Code written for earlier versions that accesses `n.model.variables["Line-p"]` will fail with a KeyError.

## Context

Discovered during B-1 (flow gate custom constraint). The test spec referenced `n.model.variables["Line-p"]` based on earlier API documentation. Running the test produced: `ValueError: Line-p variable not found in model. Available: ['Generator-p', 'Line-s', 'Transformer-s']`. After switching to `Line-s`, the test passed.

## Implications

The `doc-gaps` finding is relevant to Accessibility (D-2 documentation audit) and Maturity (E-6 CI/test coverage). Practitioners who follow older PyPSA tutorials or the pre-v1.0 API will hit this variable rename without a helpful error message. The variable name change reflects PyPSA's move to apparent-power-based line constraints, but the migration guidance in docs is sparse.
