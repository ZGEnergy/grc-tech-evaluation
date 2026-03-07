---
test_id: D-2
tool: pandapower
dimension: accessibility
network: N/A
protocol_version: "v4"
status: qualified_pass
workaround_class: stable
wall_clock_seconds: null
peak_memory_mb: null
loc: null
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# D-2: Documentation Audit

## Result: QUALIFIED PASS

## Finding

Of the 11 Suite A tests, 4 were completable using only official pandapower documentation
(https://pandapower.readthedocs.io). The 5 tests that FAIL do so because the features do
not exist in pandapower at all -- the docs correctly do not claim these capabilities. For
the 2 remaining passing tests (A-3 DC OPF, A-7 contingency sweep), source code inspection
was needed to understand convergence flags and internal data structures.

## Evidence

| Test | Status | Docs Sufficient? | Notes |
|------|--------|-------------------|-------|
| A-1 (DCPF) | PASS | Yes | `rundcpp()`, `res_bus`, `res_line` well documented |
| A-2 (ACPF) | PASS | Yes | `runpp()` with `algorithm`, `init` params documented |
| A-3 (DC OPF) | QUALIFIED PASS | Partially | `rundcopp()` documented, but convergence via `net["OPF_converged"]` vs `net["converged"]` not obvious from docs. Objective via `net.res_cost` (attribute, not DataFrame) required source inspection. |
| A-4 (AC feasibility) | PASS | Yes | Follows from A-2 + A-3 docs. In-place gen `p_mw` modification is idiomatic pandas. |
| A-5 (SCUC) | FAIL | N/A | Feature does not exist. Docs correctly omit it. |
| A-6 (SCED) | FAIL | N/A | Depends on A-5. Feature does not exist. |
| A-7 (Contingency) | PASS | Partially | `topology.create_nxgraph()` documented. In-service toggling via `net.line["in_service"]` requires knowing pandapower's DataFrame model; docs cover it but scatteredly. |
| A-8 (Stochastic OPF) | FAIL | N/A | Feature does not exist. |
| A-9 (SCOPF) | FAIL | N/A | Feature does not exist. |
| A-10 (Lossy DC OPF) | FAIL | N/A | Feature does not exist. |
| A-11 (Distributed slack OPF) | FAIL | N/A | `distributed_slack` param documented for `runpp()` but does not exist for `rundcopp()`/`runopp()`. Docs do not clarify this asymmetry. |

**Specific documentation gaps identified:**

1. **OPF convergence flag asymmetry (observation A-3):** Power flow uses `net["converged"]`;
   OPF uses `net["OPF_converged"]`. The OPF docs do not prominently call out this difference.
   A user following PF docs patterns would check the wrong flag.

2. **OPF objective access (observation A-3):** `net.res_cost` is an attribute (float), not a
   DataFrame like other `res_*` attributes. Not documented alongside the OPF tutorial.

3. **OPF constraint duals (observation B-1):** Line flow constraint dual values are only
   accessible via `net._ppc["branch"]` at PYPOWER column indices 17/18. This is not in the
   public API or docs.

4. **`distributed_slack` parameter scope (observation A-11):** Available for `runpp()` but
   silently swallowed by `**kwargs` in `rundcopp()`/`runopp()` (observation B-8). No
   warning emitted. Docs do not state which functions support it.

5. **PWL cost format (observation P2-2):** The piecewise-linear cost format
   (`[[p_start, p_end, marginal_cost]]`) differs from MATPOWER convention and is not
   well-documented.

**Documentation quality for covered features:**

- Power flow (`runpp`, `rundcpp`) documentation is comprehensive with examples.
- Network element creation (`create_bus`, `create_line`, etc.) is well-documented with
  parameter descriptions and default values.
- Standard library networks (`pp.networks.*`) are listed and accessible.
- OPF documentation exists but has the gaps noted above.
- The v3.0.0 breaking change (kW to MW unit convention) is documented in release notes but
  not prominently flagged in tutorials.

## Workarounds

- **What:** Source code inspection needed for OPF convergence flags and result access patterns.
- **Why:** Documentation does not fully cover the OPF API surface, particularly the
  `OPF_converged` vs `converged` flag distinction and `res_cost` access pattern.
- **Durability:** stable -- these are stable internal patterns unlikely to change.
- **Grade impact:** Minor. The gaps affect OPF users specifically, not the broader PF user base.

## Implications

pandapower documentation is strong for its core use case (power flow analysis) but has
meaningful gaps for OPF features. The 5 FAIL tests represent absent capabilities, not
documentation failures. For the features that exist, 4 of 6 passing tests were completable
from docs alone. The 2 requiring source inspection involved OPF-specific patterns that are
stable but underdocumented. This supports a qualified pass: docs are good for PF, adequate
but incomplete for OPF.
