---
tag: workaround-needed
source_dimension: fnm_ingestion
source_test: G-FNM-1
tool: pandapower
severity: medium
timestamp: 2026-03-14T03:00:00Z
---

# Observation: pandapower 3.4.0 from_ppc has IndexError bug on zero RATE_A branches

## Finding

pandapower 3.4.0's `_from_ppc_branch` function in the PYPOWER converter has a
variable naming collision: the impedance processing block reuses the variable name
`sn_is_zero` (computed from `sn_mva` for impedance elements) but then indexes into
`sn` (from the transformer block, which has a different size), causing an
`IndexError: boolean index did not match indexed array along axis 0`. This triggers
whenever any branch has RATE_A = 0.

## Context

The FNM network has 28 branches with RATE_A = 0 (no thermal limit specified).
When these are passed to `from_ppc()`, the bug at line 129 of
`pandapower/converter/pypower/from_ppc.py` is triggered. The workaround is to
pre-set zero RATE_A values to a large sentinel (9999.0) before calling `from_ppc()`.
This is a deterministic, stable workaround that does not affect power flow accuracy.

## Implications

This bug affects any user loading MATPOWER/PYPOWER cases with zero-rated branches
into pandapower 3.4.0. It is likely a regression in the 3.x series. The workaround
is stable and straightforward, but the bug should be noted in the accessibility
dimension as evidence of converter robustness issues on large real-world networks.
