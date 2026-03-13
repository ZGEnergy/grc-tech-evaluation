---
tag: api-friction
dimension: expressiveness
test_id: A-3
network: MEDIUM
timestamp: 2026-03-11T00:00:00Z
---

# Observation: overwrite_zero_s_nom Value Selection Critical for OPF on ACTIVSg10k

## Finding

The `overwrite_zero_s_nom` parameter in `import_from_pypower_ppc()` requires careful value selection for OPF on ACTIVSg10k. Using `True` (equivalent to 1.0 MVA) causes OPF infeasibility because the 2,462 zero-rated lines carry up to 1,840 MW of real power flow in the base case. The correct value for OPF is a large number (e.g., 9,999 MVA) to make these lines effectively unconstrained.

## Evidence

- `overwrite_zero_s_nom=True` → OPF status: **Infeasible** (immediate presolve detection)
- `overwrite_zero_s_nom=9999.0` → OPF status: **Optimal** (5,187 simplex iterations)
- Base-case DCPF: max line flow 1,839 MW; zero-rated lines carry real flows
- Lines with original s_nom = 0: 2,462 (25.3% of all 9,726 lines)

## Implications

The `overwrite_zero_s_nom` parameter behavior is documented (float or None), but the appropriate value for a given network is not obvious. For DCPF/ACPF, any positive value works since flow limits are not enforced. For OPF, the value must exceed the maximum expected flow on these branches. This is a non-obvious API friction point that could cause silent OPF failures for users who use `overwrite_zero_s_nom=True` or a small value.

This is also relevant for other large synthetic networks (ACTIVSg2000, etc.) that may have similar zero-rated branch patterns.
