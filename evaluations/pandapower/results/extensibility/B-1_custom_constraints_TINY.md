---
test_id: B-1
tool: pandapower
dimension: extensibility
network: TINY
protocol_version: "v4"
status: qualified_pass
workaround_class: fragile
wall_clock_seconds: 0.223
peak_memory_mb: null
loc: 192
solver: PYPOWER interior point
timestamp: 2026-03-06T00:00:00Z
---

# B-1: Add a flow gate limit to DC OPF, read and assert on dual value

## Result: QUALIFIED PASS

## Approach

Two aspects were tested: (1) adding a flow constraint to the DC OPF, and (2) extracting the dual (shadow price) of that constraint.

**Adding the constraint:** pandapower supports per-line flow limits via the public `max_i_ka` attribute on `net.line`. Setting `net.line.at[idx, "max_i_ka"]` to a value that corresponds to the desired MW limit (converted via `P = sqrt(3) * V * I`) constrains that line in `rundcopp()`. This is a documented, public API for individual line limits. However, pandapower has no API for an aggregate flow gate constraint (sum of flows across multiple lines). True aggregate constraints would require PYPOWER `userfcn` callbacks operating at the internal `ppc` level.

**Extracting dual values:** The `net.res_line` DataFrame does not contain dual/shadow price columns. Duals are accessible only through the internal `net._ppc["branch"]` array at PYPOWER column indices MU_SF (17) and MU_ST (18). This uses the private `_ppc` attribute and undocumented PYPOWER column layout.

### Constraint Setup

Lines 0, 1, 2 were selected as a flow gate corridor. Per-line limits were set to 70% of the aggregate base-case flow, divided equally among the three lines (261.2 MW each via `max_i_ka`).

## Output

| Metric | Value |
|--------|-------|
| Base case objective | 41,263.94 |
| Constrained objective | 44,126.28 |
| Objective increase | 2,862.34 (6.9%) |
| Base case gate flow (abs sum) | 1,119.4 MW |
| Constrained gate flow (abs sum) | 611.3 MW |
| Flow reduction | 45.4% |

Binding constraint report:

| Line | Loading % | MU_SF (dual) | MU_ST (dual) |
|------|-----------|-------------|-------------|
| 0 | 85.7% | 0.0 | 0.0 |
| 1 | 48.3% | 0.0 | 0.0 |
| 2 | 100.0% | 38.46 | 0.0 |

Line 2 is binding at 100% loading with a non-zero shadow price of 38.46, confirming the constraint is active and the dual is extractable. Lines 0 and 1 are non-binding.

LMPs show locational price separation (range 5.94 to 36.64) due to the binding constraint, compared to the uniform 13.52 in the unconstrained base case.

## Workarounds

- **What:** Per-line flow limits via `max_i_ka` (public API) used as proxy for an aggregate flow gate constraint. True aggregate constraint (sum of flows <= limit) is not available without PYPOWER `userfcn` callback at the `ppc` level.
- **Why:** pandapower has no API for aggregate linear constraints across multiple branches in OPF.
- **Durability:** stable -- `max_i_ka` is a documented public attribute that controls line limits in OPF.
- **Grade impact:** Per-line limits are a reasonable proxy but not a true aggregate flow gate.

- **What:** Dual values extracted from `net._ppc["branch"][:, 17]` (MU_SF column in PYPOWER branch array).
- **Why:** `net.res_line` does not expose shadow prices for line flow constraints. The only path is through the private `_ppc` internal data structure using PYPOWER column index conventions.
- **Durability:** fragile -- relies on `_ppc` (private attribute with leading underscore) and PYPOWER's undocumented column layout. Could break on version updates.
- **Grade impact:** The dual IS extractable, but only through undocumented internals.

## Timing

- **Wall-clock:** 0.223 s (two DC OPF solves: base case + constrained)
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/pandapower/tests/extensibility/test_b1_custom_constraints.py`
