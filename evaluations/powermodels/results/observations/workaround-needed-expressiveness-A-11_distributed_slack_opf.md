---
tag: workaround-needed
dimension: expressiveness
test_id: A-11
slug: distributed_slack_opf
tool: powermodels
network: TINY
---

# workaround-needed: No native distributed slack support

## Finding

PowerModels has no distributed slack bus support in any formulation (PF, OPF, or
native compute functions). All formulations use a single reference bus (bus_type=3).
There is no API parameter, configuration option, or extension point to distribute
slack across multiple buses. GitHub issues #989 and #932 confirm this limitation.

## Workaround

Manually construct a PTDF-based DC OPF via JuMP using a distributed-slack PTDF
matrix derived from PowerModels' single-slack `calc_basic_ptdf_matrix`:

```

H_dist = H_single - H_single * w

```

where `w` is a user-defined slack weight vector (e.g., load-proportional).

The workaround requires ~150 lines of JuMP code to build the full OPF with power
balance, PTDF-based flow limits, and cost objective. LMPs are extracted from JuMP
duals on the power balance and flow limit constraints.

## Effort

High. The entire OPF formulation must be rebuilt manually. PowerModels contributes
only data parsing, network utilities, and the single-slack PTDF matrix.

## Stability

Stable. The mathematical approach (PTDF with distributed slack weights) is well-established
in power systems literature. The JuMP-based implementation is straightforward once
the algebra is understood. However, this bypasses all of PowerModels' formulation
infrastructure, reducing the value of the tool for this use case.
