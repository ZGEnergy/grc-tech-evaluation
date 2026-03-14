---
tag: workaround-needed
source_dimension: expressiveness
source_test: A-10
tool: matpower
severity: high
timestamp: 2026-03-13T00:00:00Z
---

# Observation: No internal loss model in DC OPF prevents LMP decomposition

## Finding

MATPOWER's DC OPF formulation has no internal loss model. Branch resistance is ignored in the B-matrix construction (`makeBdc` uses only reactance). While total losses can be approximated via iterative loss injection, the loss effect cannot be distinguished from load in the LMP decomposition, making the marginal loss component identically zero.

## Context

Test A-10 required loss-inclusive LMPs decomposed into energy, congestion, and loss components. The iterative loss injection approach produces correct total losses (0.70% of load) and a higher objective ($225,954 vs $219,748), but the loss injections are treated as ordinary load by the solver, producing zero loss residual in the LMP decomposition.

## Implications

- **Extensibility:** Adding a true loss model to MATPOWER DC OPF would require modifying the power balance equations in `opf_setup.m`, which is a source-code change (blocking workaround class).
- **Accessibility:** The `get_losses()` function exists but only works for AC power flow results, not DC OPF — this gap is not documented.
