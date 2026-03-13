---
tag: doc-gaps
source_dimension: extensibility
source_test: B-9
tool: pypsa
severity: high
timestamp: 2026-03-11T00:00:00Z
---

# Observation: Phase-shift and off-nominal-tap correction vectors undocumented for PTDF prediction

## Finding

On networks with phase-shifting transformers or off-nominal-tap transformers (ACTIVSg10k has 5 and 970 respectively), the naive PTDF flow prediction formula `PTDF @ P_inj_pu` produces errors up to 7.43 pu (743 MW at 100 MVA base). The correct formula requires two undocumented correction vectors exposed as `sn.p_bus_shift` (MW) and `sn.p_branch_shift` (MW):

```python
flow_pu = PTDF @ (P_inj_pu - p_bus_shift / BASE_MVA) + p_branch_shift / BASE_MVA
```

With this correction, max error on ACTIVSg10k is 5.2e-11 pu (machine precision).

## Context

Discovered during B-9 MEDIUM testing on ACTIVSg10k. The TINY test (case39) has no phase-shifting transformers, so the simple formula worked. At MEDIUM scale with a realistic transmission network, the correction is mandatory. The attributes `p_bus_shift` and `p_branch_shift` are accessible on the sub_network object after `calculate_PTDF()` but are not mentioned in any user-facing PTDF documentation.

The cross-tool-watchpoints.md formula (`flow_pu = PTDF @ (P_inj_pu - Pbusinj) + Pfinj`) maps exactly to PyPSA's correction vectors, but the attribute names are undiscoverable without reading PyPSA source code (`pf.py`).

## Implications

Any practitioner using PTDF for flow prediction, sensitivity analysis, or contingency screening on a real-world transmission network (which will have off-nominal taps) will silently produce incorrect results unless they discover these correction vectors independently. The severity is high because the error is large (7.43 pu on ACTIVSg10k) and silent — no warning is raised. The Accessibility audit (D-2, D-4) should test whether PTDF documentation covers phase-shift networks.
