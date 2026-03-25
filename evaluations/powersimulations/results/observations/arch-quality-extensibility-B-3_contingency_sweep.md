---
tag: arch-quality
source_dimension: extensibility
source_test: B-3
tool: powersimulations
severity: medium
timestamp: 2026-03-24T00:00:00Z
---

# Observation: LODF matrix enables contingency screening without model reconstruction

## Finding

PowerNetworkMatrices.jl's `LODF(sys)` provides a pre-computed line outage distribution
factor matrix that enables fast post-contingency flow estimation without model reconstruction.
However, no built-in multi-outage correction (Woodbury formula) exists, limiting accuracy
for N-M (M>1) contingency analyses to the superposition approximation.

## Context

During B-3 (N-M contingency sweep), 1,299 pruned contingency cases were evaluated in
0.43 seconds using LODF superposition. The LODF matrix is indexed by branch name strings,
making it straightforward to map between contingency sets and flow estimates. The lack of
Woodbury correction means M>1 results are approximate screening values.

## Implications

For the Maturity audit: the clean separation of concerns (PowerFlows for base case,
PowerNetworkMatrices for sensitivity factors, PowerSystems for data) is an architectural
positive. The absence of built-in N-M exact analysis is a gap but consistent with the
tool's focus on production-cost simulation rather than reliability analysis.
