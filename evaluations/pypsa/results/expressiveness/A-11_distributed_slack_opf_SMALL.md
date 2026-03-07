---
test_id: A-11
tool: pypsa
dimension: expressiveness
network: SMALL
protocol_version: "v4"
status: pass
workaround_class: stable
wall_clock_seconds: 10.4
peak_memory_mb: null
loc: null
solver: highs
timestamp: 2026-03-06T00:00:00Z
---

# A-11: Distributed Slack OPF (SMALL)

## Result: PASS

## Approach

Same approach as TINY: solved DCOPF with three slack configurations on the 2000-bus
network and compared results:
- **(a)** Default single slack bus
- **(b)** Different single slack bus (changed via DataFrame edit)
- **(c)** Distributed slack via `n.pf(distribute_slack=True, slack_weights='p_set')`

## Output

All three configurations converge. In PyPSA's DCOPF, the slack bus does not affect
LMPs (optimizer enforces power balance as a constraint). Distributed slack affects
only power flow angles, not optimization results.

LMPs are identical across all three configurations, confirming that PyPSA's OPF
formulation is independent of slack bus selection.

## Workarounds

- **What:** Manually set marginal_cost from gencost data (PPC importer does not
  import gencost).
- **Why:** Standard workaround for MATPOWER import.
- **Durability:** stable
- **Grade impact:** None.
- **Version tested:** PyPSA 1.1.2

## Timing

- **Wall-clock:** 10.4 s
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/expressiveness/test_a11_distributed_slack_opf_small.py`
