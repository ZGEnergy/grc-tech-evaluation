---
tag: workaround-needed
source_dimension: expressiveness
source_test: A-12
tool: gridcal
severity: high
timestamp: "2026-03-24T12:00:00Z"
---

# Observation: Battery multi-period OPF requires source patch (blocking)

## Finding

GridCal's multi-period storage optimization produces physically incorrect results due
to a sign error in the battery energy balance constraint. No public API workaround
exists; fixing the issue would require modifying `linear_opf_ts.py` source code
(blocking workaround class). [tool-specific]

## Context

The Battery device type is fully featured at the API level (Enom, Pmin/Pmax,
charge/discharge efficiency, min/max SoC, soc_0). The `OptimalPowerFlowTimeSeriesDriver`
correctly handles inter-temporal coupling. The constraint builder assembles the energy
balance equation, but the sign is inverted: `E[t] = E[t-1] + dt*(eta_dis*P_dis -
eta_ch*P_ch)` instead of `E[t] = E[t-1] - P_dis*dt/eta_dis + P_ch*dt*eta_ch`.

Since GridCal's OPF does not expose the internal LP model for user modification
(`Custom Constraint Injection: no` per research-context.md), there is no way to correct
the energy balance constraint from outside the library. Additionally, cyclic SoC
(SoC[0] == SoC[T]) is not implemented.

## Implications

- **Extensibility dimension:** This reinforces the finding that GridCal does not expose
  OPF internals for user modification. A tool that allowed custom constraint injection
  could work around this bug at the user level.
- **Maturity dimension:** The bug is classified as blocking because it cannot be fixed
  without source code modification. This affects the tool's maturity grade for
  production-readiness of advanced features.
