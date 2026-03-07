---
test_id: A-9
tool: pypsa
dimension: expressiveness
network: SMALL
protocol_version: "v4"
status: pass
workaround_class: stable
wall_clock_seconds: 70.0
peak_memory_mb: null
loc: null
solver: highs
timestamp: 2026-03-06T00:00:00Z
---

# A-9: Security-Constrained OPF (SMALL)

## Result: PASS

## Approach

Used `n.optimize.optimize_security_constrained(branch_outages=monitored_branches)`
on the ACTIVSg 2000-bus network with 50 monitored branches (selected by highest
base-case flow utilization). Contingency constraints are embedded in the LP — they
are part of the optimization, not checked post-hoc.

Thermal ratings scaled to 150% of original s_nom (same protocol as TINY) to achieve
feasibility.

## Output

- **Solver status:** optimal
- **Wall-clock:** ~70 s
- **Contingency set:** 50 branches (highest base-case utilization)
- **SCOPF objective vs unconstrained DCOPF:** SCOPF ~0.4% more expensive
- **Dispatch:** Differs from unconstrained DCOPF — generation redistributed to
  satisfy N-1 contingency constraints

The SCOPF successfully scales to SMALL (2000-bus) with 50 monitored contingencies.
The solver time is reasonable (~70s) for a single-threaded HiGHS solve.

## Workarounds

- **What:** Scaled thermal ratings to 150% of s_nom; selected 50 monitored branches
  (not full N-1 on all 2,359 branches).
- **Why:** Full N-1 contingency set on 2000-bus is computationally prohibitive.
  Rating relaxation needed for feasibility.
- **Durability:** stable — `optimize_security_constrained()` is a documented first-class API.
- **Grade impact:** None. Contingency set selection and rating relaxation are
  protocol-permitted.
- **Version tested:** PyPSA 1.1.2

## Timing

- **Wall-clock:** ~70 s
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/expressiveness/test_a9_scopf_small.py`
