---
tag: fnm-data-model
source_dimension: fnm_ingestion
source_test: G-FNM-4
tool: gridcal
severity: medium
timestamp: 2026-03-24T00:00:00Z
---

# Observation: ACPF fails to converge on FNM -- possible MATPOWER fallback data fidelity issue

## Finding

GridCal's ACPF solver (Newton-Raphson, Levenberg-Marquardt, HELM) fails to converge
on the 27,862-bus FNM main island loaded via MATPOWER fallback path. The best result
(LM, 200 iterations) achieves a residual of 15.83 MVA, far from the 1e-6 tolerance.

## Context

G-FNM-4 tested ACPF convergence with DCPF warm-start and progressive branch rate
relaxation (0%, 10%, 20%). Four solver algorithms were exercised. None achieved
genuine convergence at any relaxation level. Key diagnostic indicators:

- Newton-Raphson: stalled at residual ~615, voltage oscillations (VM 0.001 to 12.8 pu)
- Levenberg-Marquardt: best residual 15.83, VM range [0.032, 1.57] -- closest to physical
- HELM: immediate divergence (residual 94,856, VM up to 300 pu)
- Branch rate relaxation had zero effect (rates are thermal limits, not ACPF parameters)

The false convergence detection in `retry_with_other_methods=True` mode is also notable:
the solver reports convergence after 1 iteration with a residual of 582, which is a
diagnostic quality concern.

## Implications

The ACPF failure may be partially attributable to data loss in the MATPOWER format:
transformer tap control modes, winding impedance detail, and switched shunt discrete
steps are ACPF-critical (Tier 2) fields that are flattened or lost in .m format.
Tools evaluating via direct PSS/e `.raw` ingestion (e.g., if GridCal's RAW parser
were used) might achieve better ACPF results on the same network. This finding should
inform the fnm_ingestion dimension's assessment of MATPOWER fallback adequacy for AC
analysis.
