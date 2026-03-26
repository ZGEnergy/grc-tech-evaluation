---
tag: api-friction
source_dimension: expressiveness
source_test: A-11
tool: gridcal
severity: high
timestamp: "2026-03-24T00:00:00Z"
---

# Observation: Distributed slack option exists in PF but is ignored by OPF

## Finding

GridCal's `PowerFlowOptions.distributed_slack` flag is functional for power flow (DCPF/ACPF)
but has no effect on the linear OPF formulation. The OPF code (`linear_opf_ts.py`, line 3022)
hardcodes `distributed_slack=False` when constructing the `LinearAnalysis` for PTDF
computation. Setting `power_flow_options.distributed_slack=True` on the OPF options silently
produces identical results to the single-slack case.

## Context

During A-11 (distributed slack OPF), setting the distributed_slack flag on the OPF's embedded
power_flow_options had zero effect on dispatch or LMPs. Source code inspection confirmed the
flag is not plumbed through to the OPF formulation. This creates a misleading API surface
where the option appears configurable but is silently ignored.

## Implications

The Accessibility audit should note this as a doc-gap: the API surface suggests distributed
slack is configurable for OPF, but it is not. Users who set this flag expecting distributed
slack LMPs will get single-slack results without any warning or error. The Extensibility
assessment (B-1) should note that implementing distributed slack in OPF would require
modifying `linear_opf_ts.py` source code -- there is no hook or configuration path to
achieve this through the public API.
