---
tag: api-friction
dimension: expressiveness
test_id: A-11
slug: distributed_slack_opf
tool: powermodels
network: TINY
---

# api-friction: Dual sign convention inconsistency

## Finding

PowerModels reports LMPs (bus power balance duals via `lam_kcl_r`) with negative sign
convention, while manual JuMP-based OPF formulations using the same solver produce
positive duals. This sign inconsistency creates confusion when comparing results
between PowerModels' built-in OPF and user-assembled JuMP formulations.

In the A-11 test:
- PowerModels single-slack LMP at ref bus: -1351.692
- Manual distributed-slack LMP at ref bus: +1351.692

The absolute values are consistent, but the sign flip requires awareness of dual
conventions and complicates result validation.

## Additional Friction

The `calc_basic_ptdf_matrix` function operates on a "basic network" (contiguous
bus numbering, no isolated components) which requires calling `make_basic_network()`
first. The bus ordering in the basic network must be tracked to correctly map PTDF
rows/columns back to original bus IDs. This mapping is not documented and must be
inferred from the data structure.
