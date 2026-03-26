---
tag: cascaded-failure
source_dimension: scalability
source_test: C-10
tool: pypsa
severity: high
timestamp: 2026-03-24T12:00:00Z
---

# Observation: Distributed Slack OPF Blocked at MEDIUM Scale (Cascaded from A-11)

## Finding

PyPSA's distributed slack DC OPF limitation discovered in A-11 (TINY) cascades
unchanged to C-10 (MEDIUM). The linopy model lacks Bus-v_ang variables, making
distributed slack OPF architecturally impossible regardless of network size.

## Context

C-10 tests distributed slack DC OPF on ACTIVSg10k (10,000 buses). The linopy model
variables are `Generator-p`, `Line-s`, and `Transformer-s` — no `Bus-v_ang`. The DC
OPF uses cycle constraints (KVL) on line-flow variables rather than bus angle
variables, so there is no angle reference constraint to distribute.

Single-slack DC OPF works correctly at MEDIUM scale ($1,306,775 objective, 6,017
distinct LMPs). The limitation is specifically the distributed slack formulation.

## Implications

This is a tool-specific architectural limitation, not a solver limitation. It affects
the Scalability grade for C-10 and should be cross-referenced with A-11 in the
Expressiveness dimension. The synthesis report should note that PyPSA cannot produce
distributed slack LMPs in the OPF context at any network scale.
