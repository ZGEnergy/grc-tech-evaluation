---
tag: solver-issues
source_dimension: expressiveness
source_test: A-12
tool: gridcal
severity: high
timestamp: "2026-03-24T12:00:00Z"
---

# Observation: Battery energy balance formulation sign error in linear OPF

## Finding

GridCal's linear OPF battery formulation (`linear_opf_ts.py`, line ~1776) has an
inverted sign in the energy balance constraint: discharge adds energy rather than
removing it. This produces physically incorrect multi-period storage optimization
results where the battery always discharges at maximum power. This is [tool-specific],
not a solver limitation.

## Context

During A-12 (multi-period DCOPF with storage), a Battery device was correctly
configured at bus 5 with 150 MW / 600 MWh and proper efficiency parameters
(eta_ch=0.92, eta_dis=0.95). The OPF converged for all 24 hours, but the battery
discharged at 150 MW continuously with no charging. Stored energy increased from
300 to 303 MWh during 24 hours of continuous discharge -- the opposite of physical
behavior.

The formulation reads:
`E[t] = E[t-1] + dt * (eta_dis * P_dis - eta_ch * P_ch)`

Correct formulation should be:
`E[t] = E[t-1] - P_dis * dt / eta_dis + P_ch * dt * eta_ch`

Both the sign and the efficiency placement are wrong. Additionally, no cyclic SoC
constraint (SoC[0] == SoC[T]) is present in the formulation.

## Implications

- **Scalability dimension:** Any scalability test involving storage or multi-period
  optimization (C-suite) will be affected by the same formulation bug. Storage-related
  scalability results cannot be trusted.
- **Maturity dimension:** A sign error in a core formulation that ships in the released
  package (v5.6.28) indicates insufficient unit testing of the battery OPF formulation.
  This is relevant to software quality assessment.
- **Accessibility dimension:** The bug is not documented in any release notes or known
  issues. Users relying on the Battery device for multi-period OPF will silently get
  incorrect results with no warning or diagnostic.
