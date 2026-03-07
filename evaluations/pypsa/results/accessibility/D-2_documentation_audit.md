---
test_id: D-2
tool: pypsa
dimension: accessibility
network: N/A
protocol_version: "v4"
status: qualified_pass
workaround_class: null
wall_clock_seconds: null
peak_memory_mb: null
loc: null
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# D-2: Documentation Audit

## Objective

For each Suite A test (A-1 through A-11), determine whether a user could
complete it using ONLY official PyPSA documentation (no source code reading
required).

## Assessment per Test

### A-1 DCPF: `n.lpf()`
**Documented: YES.** Dedicated user-guide page (`user-guide/linear-power-flow/`)
describes `n.lpf()`, its assumptions, and inputs/outputs. Quickstart 2 covers
power flow.

### A-2 ACPF: `n.pf()`
**Documented: YES.** User-guide page (`user-guide/power-flow/`) covers
Newton-Raphson AC power flow, bus types (PQ/PV/Slack), convergence parameters,
and `distribute_slack` option.

### A-3 DCOPF: `n.optimize()`
**Documented: PARTIALLY.** The optimization overview and quickstart notebooks
demonstrate `n.optimize()` and show bus marginal prices in results. However:
- Line shadow prices (`mu_upper`/`mu_lower`) are not documented as network
  outputs -- the solver logs even say they "were not assigned to the network."
- LMP decomposition into energy/congestion components requires accessing Linopy
  model internals, which is undocumented.
- The PPC importer silently drops `gencost` data (observation A-3 from
  api-friction), which is not warned about in docs.

### A-4 AC Feasibility: Run PF on OPF dispatch
**Documented: PARTIALLY.** The function
`n.optimize.optimize_and_run_non_linear_powerflow()` exists and is referenced in
the power flow docs. However, the two-step workflow (run OPF, then validate with
AC PF) is not presented as an explicit tutorial. A user could piece it together
from separate pages.

### A-5 SCUC: Committable generators
**Documented: YES.** Dedicated optimization sub-page
(`user-guide/optimization/unit-commitment/`) documents all UC parameters:
`committable`, `min_up_time`, `min_down_time`, `start_up_cost`,
`shut_down_cost`, `ramp_limit_up/down`, `p_min_pu`. A worked example notebook
exists at `examples/unit-commitment/`.

### A-6 SCED: Two-stage UC then ED
**Documented: NO.** There is no documented workflow for fixing a commitment
schedule from SCUC and re-solving as an economic dispatch. The workaround
(encoding commitment into `p_min_pu`/`p_max_pu`) requires understanding of the
optimization internals. Observation A-6 from api-friction confirms this gap.

### A-7 Contingency Sweep: `n.lpf_contingency()`
**Documented: YES.** The linear power flow page documents `n.lpf_contingency()`
with its `branch_outages` parameter and BODF methodology.

### A-8 Stochastic Optimization
**Documented: YES (as of v1.x).** Dedicated page
(`user-guide/optimization/stochastic/`) documents `n.set_scenarios()`,
`n.set_risk_preference()`, and the two-stage stochastic programming formulation.
An example notebook exists at `examples/stochastic-optimization/`. However,
observation A-8 from doc-gaps notes that the `n.scenarios` data model and
optimizer integration had gaps in earlier versions.

### A-9 SCOPF: `n.optimize.optimize_security_constrained()`
**Documented: PARTIALLY.** The method exists and is referenced in the
network-optimization user guide as "Security-Constrained LOPF." API signature
shows `branch_outages` parameter. However, no dedicated tutorial or worked
example was found in the sitemap. Users would need to discover the method via
API reference.

### A-10 Lossy DCOPF: `transmission_losses` parameter
**Documented: PARTIALLY.** The parameter `transmission_losses` appears in the
`n.optimize()` signature but no dedicated documentation page for transmission
loss modeling was found in the sitemap (141 pages indexed). Users would need to
discover it via the API reference or docstring.

### A-11 Distributed Slack OPF
**Documented: PARTIALLY.** The `distribute_slack` parameter is documented for
`n.pf()` (AC power flow). For the optimization path, no explicit documentation
was found. The observation B-8 from api-friction notes that slack bus assignment
behavior in OPF is underdocumented.

## Summary Table

| Test | Docs Coverage | Could Complete from Docs Alone? |
|------|--------------|-------------------------------|
| A-1  | Full         | Yes                           |
| A-2  | Full         | Yes                           |
| A-3  | Partial      | Mostly (LMP decomposition: no)|
| A-4  | Partial      | Yes (with effort)             |
| A-5  | Full         | Yes                           |
| A-6  | None         | No                            |
| A-7  | Full         | Yes                           |
| A-8  | Full         | Yes                           |
| A-9  | Partial      | With difficulty               |
| A-10 | Partial      | With difficulty               |
| A-11 | Partial      | With difficulty               |

## Verdict

**QUALIFIED PASS.** Core workflows (PF, OPF, UC, contingency, stochastic) are
well-documented with dedicated pages and example notebooks. However, several
advanced features (SCED two-stage workflow, LMP decomposition, transmission
losses, SCOPF) lack tutorial-level documentation and require API exploration or
source code reading. The A-6 SCED workflow is the most significant gap -- no
documentation exists for the required workaround pattern.
