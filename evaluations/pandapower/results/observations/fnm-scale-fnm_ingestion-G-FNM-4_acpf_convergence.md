---
tag: fnm-scale
source_dimension: fnm_ingestion
source_test: G-FNM-4
tool: pandapower
severity: medium
timestamp: 2026-03-24T12:00:00Z
---

# Observation: pandapower ACPF non-convergence on ~28,000-bus FNM

## Finding

pandapower's internal Newton-Raphson solver fails to converge on the ~28,000-bus FNM main
island at all three progressive relaxation levels (0%, 10%, 20%). The network is
numerically ill-conditioned for ACPF, with DCPF angles reaching 536.9 degrees maximum
absolute value.

## Context

G-FNM-4 attempted ACPF convergence using DCPF warm-start (`init="results"`) followed by
progressive thermal limit relaxation. pandapower uses its own internal Newton-Raphson
implementation (PYPOWER heritage), not an external NLP solver like Ipopt. The solver
reaches 100 iterations without convergence at all relaxation levels. Contributing factors
include: (1) PPC import path data loss (flattened transformer data), (2) localized topology
anomalies identified in G-FNM-3, and (3) possible Q-limit misinterpretation (QT=0/QB=0
treated as zero reactive capability).

This is an informational finding with no gate consequence per the protocol.

## Implications

The ACPF non-convergence is consistent across all pandapower NR algorithm variants. Tools
with access to Ipopt (PowerModels.jl) or with richer data ingestion paths (preserving
switched shunt and transformer tap control data) may achieve convergence on this network.
The finding is relevant to the Scalability dimension as evidence of pandapower's large-network
ACPF robustness limitations.
