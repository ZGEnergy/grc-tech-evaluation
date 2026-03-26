---
tag: solver-issues
source_dimension: scalability
source_test: C-8
tool: gridcal
severity: medium
timestamp: "2026-03-24T18:00:00Z"
---

# Observation: Soft constraints visible under branch derating; SCOPF redispatch confirmed

## Finding

With branch ratings derated to 80% to create congestion on the ACTIVSg10k MEDIUM network,
GridCal's soft-constraint behavior (previously documented in A-3 on TINY) becomes visible
at MEDIUM scale. The base-case DCOPF shows max loading of 101.87% and the SCOPF shows
102.13% -- branches slightly exceed their derated limits due to LP slack variables in the
formulation. [tool-specific: soft branch constraints allow slight overloading]

Despite the soft constraints, the SCOPF produces meaningful security-constrained redispatch:
956.5 MW aggregate dispatch change vs the base DCOPF, with 8 generators showing >1 MW
changes. The largest redispatch moves 358 MW (gen_108: +358 MW, gen_1816: -189 MW). LMP
spread increases from 144.91 to 147.03 $/MWh under SCOPF, confirming contingency constraints
are active.

## Context

The ACTIVSg10k network is uncongested at original branch ratings (max loading 84.72%).
Per the v11 protocol, branch derating to 80% creates congestion for the SCOPF test. The
80% derating factor was chosen to produce binding constraints without making the problem
infeasible. Two branches are binding (>99% loading) in both base DCOPF and SCOPF results.

SCOPF solves in 32.12 s with peak memory of 5,908 MB (15.8x the SMALL network memory).
Time scales approximately linearly with bus count (5.89x for 5x buses).

## Implications

The soft-constraint formulation means that GridCal's SCOPF does not strictly enforce
thermal limits -- branches can exceed their ratings by a small amount. This is consistent
with the A-3 finding and is a tool characteristic rather than a solver issue. For
practical use, the overloading is small (< 3%) and the redispatch behavior is correct.
The pass condition (>= 5 MW aggregate dispatch change) is met by a wide margin (956 MW).
