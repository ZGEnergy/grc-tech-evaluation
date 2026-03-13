# api-friction: B-9 PTDF — make_basic_network absorbs phase-shift angles

**Tag:** api-friction
**Dimension:** extensibility
**Test:** B-9
**Network:** MEDIUM

## Observation

ACTIVSg10k has 5 phase-shifting transformers with shifts of −7.7°, −12°, −20°, −26°, −26°. The cross-tool-watchpoints.md document warns that standard `PTDF @ Pinj` may have large errors on networks with phase-shifters, requiring Pbusinj/Pfinj correction terms.

However, after calling `make_basic_network(data)`, all 5 phase-shifting branches show `shift=0.0` in the basic network. The `make_basic_network` function integrates the phase-shift offsets into the network's reference voltage angles during the bus renumbering process. As a result, the standard formula `flow = PTDF @ Pinj` produces exact results (max error = 2.18e-11 pu) with no correction terms needed.

## Implication

The `make_basic_network` + `calc_basic_ptdf_matrix` API is "phase-shifter transparent" — it handles phase-shifting transformers internally without requiring the user to apply correction terms. This is a good user-experience property.

However, users who need to work with the phase-shift angles explicitly (e.g., for sensitivity analysis of phase-shifter tap changes) will find that the shift information is lost after `make_basic_network`. The original `data["branch"]` must be consulted to recover it.

**Discovering this behavior required running the test** — the API documentation does not clearly state whether `make_basic_network` absorbs phase-shift angles. This is a mild documentation gap.

## Recommendation

Document in B-9 results that `make_basic_network` absorbs phase-shift angles into the B-matrix reference frame. Cross-tool-watchpoints.md should note that this PowerModels-specific behavior differs from what a naive PTDF user might expect.
