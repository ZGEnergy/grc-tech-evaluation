---
tag: workaround-needed
dimension: expressiveness
test_id: A-11
tool: powermodels
---

# Workaround: No Native Distributed Slack

PowerModels does not support distributed slack natively. The A-11 test required a custom build function (~40 LOC) that replaces `constraint_theta_ref` with a load-proportional angle-sum constraint.

This is the same workaround pattern identified in B-8 (reference bus configuration). The custom build function must reproduce all standard OPF variable/constraint/objective calls (~30 lines of boilerplate) plus the custom angle constraint.

For lossless DC OPF, the distributed slack produces identical LMPs, dispatch, and objectives to single-slack -- confirming the mathematical expectation that angle reference choice is irrelevant to the optimization in the lossless case. This would differ for lossy DC OPF formulations.

The `constraint_theta_ref` function is not designed to be easily overridden; the entire build function must be replaced. A more modular build function design (e.g., hook-based constraint registration) would reduce this boilerplate.
