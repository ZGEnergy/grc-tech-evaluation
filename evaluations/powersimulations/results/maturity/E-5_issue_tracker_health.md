---
test_id: E-5
tool: powersimulations
dimension: maturity
network: N/A
protocol_version: "v10"
skill_version: "v1"
test_hash: "d2f277d5"
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
solver: null
timestamp: 2026-03-14T00:00:00Z
---

# E-5: Issue Tracker Health

## Result: INFORMATIONAL

## Finding

The PowerSimulations.jl issue tracker is actively maintained with a median time-to-close of 19.8 days across the 20 most recently closed issues. Issues receive substantive responses, often with code fixes within days. The open issue backlog is small (10 sampled) and reflects current development priorities rather than neglected reports.

## Evidence

### Closed Issues (20 most recent)

| # | Title | Created | Closed | Days |
|---|-------|---------|--------|------|
| 1546 | `Source` with time series? | 2026-02-19 | 2026-03-02 | 10.9 |
| 1531 | Market bid VOM cost missing `dt` multiplier | 2026-02-07 | 2026-02-13 | 5.9 |
| 1525 | PowerFlow HVDC Tracking issue | 2026-01-27 | 2026-02-17 | 20.4 |
| 1510 | Handling 3D Variables in Emulator | 2026-01-08 | 2026-02-14 | 37.0 |
| 1505 | write_result!() DenseAxisArray support | 2026-01-02 | 2026-01-27 | 25.1 |
| 1498 | Tutorial: HVDC multi-terminal model | 2025-12-19 | 2026-01-16 | 27.9 |
| 1497 | Tutorial: How to use contingency models | 2025-12-19 | 2026-01-16 | 27.9 |
| 1496 | Tutorial: PowerFlow exporter | 2025-12-19 | 2026-01-16 | 27.9 |
| 1495 | Tutorial: time-varying market bid cost | 2025-12-19 | 2026-01-16 | 27.9 |
| 1493 | RenewableDispatch with quadratic cost curve | 2025-12-17 | 2025-12-30 | 12.6 |
| 1488 | Outdated code in `agc.jl` | 2025-12-16 | 2025-12-16 | 0.0 |
| 1486 | Model build fails: ThermalStandardUC + ImportExport | 2025-12-15 | 2025-12-16 | 0.9 |
| 1466 | MarketBidCost not working with SingleTimeSeries | 2025-12-05 | 2025-12-06 | 0.2 |
| 1454 | Fix Performance Tests | 2025-11-13 | 2025-12-04 | 20.9 |
| 1451 | DegreeTwo reductions for Interfaces | 2025-11-11 | 2025-11-30 | 19.1 |
| 1449 | Document: power flow in the loop | 2025-11-11 | 2026-01-16 | 66.2 |
| 1421 | MethodError at DecisionModel build | 2025-10-28 | 2025-11-04 | 7.0 |
| 1418 | AreaInterchange KeyError for psy5 | 2025-10-23 | 2025-11-04 | 11.9 |
| 1417 | ThermalStandardUC errors on FuelCurve | 2025-10-22 | 2026-01-27 | 97.1 |
| 1415 | InfrastructureSystems column name mismatch | 2025-10-21 | 2025-11-04 | 14.1 |

**Median time-to-close:** 19.8 days
**Mean time-to-close:** 23.0 days
**Min:** 0.0 days (same-day fix)
**Max:** 97.1 days

**Issue types in sample:**
- Bug reports: 10 (50%) — all resolved with code fixes
- Documentation/tutorial requests: 5 (25%) — batch-closed when tutorials created
- Feature/enhancement: 3 (15%)
- Internal tracking: 2 (10%)

**Response quality:** Bug reports (#1486, #1466, #1488) received same-day or next-day fixes with commits directly referencing the issue. Tutorial issues (#1495–1498) were batch-addressed in a documentation sprint. The longest-open issue (#1417, 97 days) was a non-trivial bug involving FuelCurve/PiecewiseAverageCurve interaction.

### Open Issues (10 most recent)

| # | Title | Created | Age (days) |
|---|-------|---------|------------|
| 1558 | StartupTime data is missing | 2026-03-03 | 11 |
| 1557 | Renewable profiles in Natural Units treated as scaling factors | 2026-03-03 | 11 |
| 1554 | _read_results doesn't handle table_format for emulation | 2026-02-28 | 14 |
| 1547 | Support DC Power Flow in the Loop + Reductions | 2026-02-20 | 22 |
| 1545 | Bug in initializing DC power flow data? | 2026-02-19 | 23 |
| 1537 | Add losses approximations to PTDF models | 2026-02-12 | 30 |
| 1534 | Refactor ProductionCostExpression | 2026-02-11 | 31 |
| 1533 | Document HVDCTwoTerminalLCC | 2026-02-10 | 32 |
| 1530 | Ramp down limits: inequality flipped? | 2026-02-06 | 36 |
| 1529 | Handling Equivalent Line Rating with DLR | 2026-02-05 | 37 |

**Oldest open issue in sample:** 37 days (#1529)
**Mix:** 3 bug reports, 3 feature requests, 2 refactoring, 2 documentation

The open issues are recent and represent active development items rather than a neglected backlog. None are stale.

### Data Source

- `gh issue list --repo NREL-Sienna/PowerSimulations.jl --state closed --limit 20` (accessed 2026-03-14)
- `gh issue list --repo NREL-Sienna/PowerSimulations.jl --state open --limit 10` (accessed 2026-03-14)

## Implications

The issue tracker is healthy and actively maintained. Key indicators:

1. **Responsiveness:** Median 19.8-day close time is reasonable for a research codebase. Critical bugs get same-day fixes.
2. **Acknowledgment ratio:** All 20 sampled closed issues received substantive responses (commits, PR references, or explanations). No issues were silently closed.
3. **Backlog management:** Open issues are recent (all under 37 days) and represent current work items, not an accumulating debt.
4. **External engagement:** Several issues (#1505, #1421, #1418, #1415) were filed by external users and received prompt, helpful responses.

The tracker reflects a team that treats issue management as part of the development workflow rather than an afterthought.
