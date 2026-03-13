# Observation: arch-quality — deepcopy pattern enables efficient N-1 loop without model reconstruction

**Tag:** arch-quality
**Dimension:** extensibility
**Test:** B-3
**Severity:** positive

## Finding

PowerModels' pure-Julia data dict representation enables N-1 contingency loops via `deepcopy(data)` without any model reconstruction overhead. `deepcopy` of the case39 data dict takes 0.61 ms vs 2.82 ms for re-parsing from file — a 4.65× speedup per contingency.

The pattern is fully composable: status mutation (`br_status=0`), connectivity check (`calc_connected_components`), and DCPF solve (`compute_dc_pf`) all work on the cloned dict without reinstating from file.

For case39 (46 branches), the full N-1 loop completes in 0.128 s wall-clock (2.78 ms/contingency average). 35 contingencies converge; 11 cause islands (expected for the case39 topology).

## Evidence

- B-3 test: `deepcopy_time_s = 0.61 ms`, `parse_time_s = 2.82 ms`, `parse_vs_copy_ratio = 4.65`
- Loop wall-clock = 0.128 s for 46 contingencies
- `br_status=0` mutation and `compute_dc_pf` work correctly on cloned dict

## Implication

Positive architecture finding. The plain-dict data representation (rather than an opaque model object) means cloning is O(data_size) and requires no API knowledge beyond standard Julia. This pattern scales well to larger networks where repeated parsing would be prohibitive.
