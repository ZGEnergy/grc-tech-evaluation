---
tag: workaround-needed
source_dimension: expressiveness
source_test: A-10
tool: matpower
severity: high
timestamp: 2026-03-24T00:00:00Z
---

# Observation: No internal loss model in DC OPF prevents LMP decomposition

## Finding

MATPOWER's DC OPF formulation has no internal loss model. Branch resistance is excluded from the B-matrix construction (`makeBdc` uses only reactance). While total losses can be approximated via iterative loss injection (converged in 3 iterations to 44.07 MW / 0.70% of load), the loss effect is indistinguishable from additional load in the LMP decomposition, making the marginal loss LMP component identically zero at all buses (max |loss LMP| = 0.000000e+00).

## Context

Test A-10 required loss-inclusive LMPs decomposed into energy, congestion, and loss components. The iterative loss injection approach produces correct aggregate metrics (total losses in 0.5-3% range, lossy objective exceeds lossless by 2.82%, LMP components sum to total within numerical precision), but check (a) -- the defining feature of lossy DC OPF -- fails because the solver treats injected losses as ordinary demand.

## Implications

- **Extensibility:** Adding a true loss model would require modifying the power balance equations in the DC OPF formulation internals (`opf_setup.m`), which is a source-code change (blocking workaround class). [tool-specific: DC OPF formulation excludes resistance from B-matrix]
- **Accessibility:** The `get_losses()` function exists but only works with AC PF results, not DC OPF. This gap is not documented in the function help or manual.
- **Cross-tool comparison:** Tools with built-in lossy DC OPF (e.g., PyPSA with `marginal_cost` loss factors) will differentiate on this test.
