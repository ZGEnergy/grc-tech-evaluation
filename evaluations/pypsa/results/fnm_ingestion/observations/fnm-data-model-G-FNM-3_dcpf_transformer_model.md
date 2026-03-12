---
tag: fnm-data-model
test_id: G-FNM-3
tool: pypsa
---

# Observation: PyPSA DCPF Transformer Susceptance Includes Tap Ratio

## Finding

PyPSA's linear power flow (`lpf`) includes the transformer tap ratio in the
branch susceptance calculation (`b = 1/(x * tap_ratio)`), whereas MATPOWER's
DCPF (`makeBdc`) ignores the tap ratio entirely (`b = 1/x`). On the ERCOT FNM
with 2,358 non-unity-tap transformers, this produces systematic bus angle
deviations (mean 3.95 deg, max 61 deg) and branch flow deviations (mean 2.46
MW, max 2,292 MW) relative to the MATPOWER DCPF reference.

## Evidence

- PyPSA source (`pypsa/network/power_flow.py`): transformer `x_pu_eff = x_pu * tap_ratio`,
  then susceptance `b = 1 / x_pu_eff`.
- MATPOWER source (`makeBdc.m`): susceptance `b = 1/x` with no tap ratio factor.
- 9,481 branches classified as transformers by PyPSA (voltage level mismatch,
  non-unity tap, or phase shift). Of these, 2,358 have tap ratios != 1.0
  (range 0.7894 to 1.4165).
- Deviations propagate through the entire network, not just to directly
  affected branches.

## Implications

This is a modeling design choice, not a bug. PyPSA's treatment is arguably more
accurate for the DC approximation, but it means DCPF results will not exactly
match MATPOWER on any network with non-unity transformer taps. Cross-tool DCPF
comparisons on networks like the ERCOT FNM should account for this difference
when setting pass/fail thresholds.
