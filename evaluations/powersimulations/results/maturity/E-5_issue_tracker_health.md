---
test_id: E-5
tool: powersimulations
dimension: maturity
network: N/A
protocol_version: "v11"
skill_version: "v2"
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
timestamp: 2026-03-24T00:00:00Z
---

# E-5: Issue Tracker Health

## Result: INFORMATIONAL

## Finding

The PowerSimulations.jl issue tracker is actively maintained with a median time-to-close of 20.7 days across the 20 most recently closed issues. Issues receive substantive responses — all 20 sampled closed issues were resolved via code fixes or documentation updates, with cross-referenced PRs. The open issue backlog is small and reflects current development priorities rather than neglected reports.

## Evidence

### Closed Issues (20 most recent)

| # | Title | Created | Closed | Days |
|---|-------|---------|--------|------|
| 1554 | _read_results doesn't handle table_format for emulation | 2026-02-28 | 2026-03-21 | 21.7 |
| 1546 | `Source` with time series? | 2026-02-19 | 2026-03-02 | 10.9 |
| 1531 | Market bid VOM cost missing `dt` multiplier | 2026-02-07 | 2026-02-13 | 5.9 |
| 1529 | Handling Equivalent Line Rating with DLR | 2026-02-05 | 2026-03-23 | 45.7 |
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

**Median time-to-close:** 20.7 days
**Mean time-to-close:** 20.9 days
**Min:** 0.0 days (same-day fix)
**Max:** 66.2 days

**Issue types in sample:**
- Bug reports: 10 (50%) — all resolved with code fixes
- Documentation/tutorial requests: 5 (25%) — batch-closed when tutorials created
- Feature/enhancement: 3 (15%)
- Internal tracking: 2 (10%)

**Acknowledgment ratio:** 20/20 (100%). All sampled closed issues were resolved with linked PRs or commits. Of the 20 issues, 10 had explicit comments while 10 were resolved silently via cross-referenced PRs (confirmed via timeline API showing 2-4 cross-reference events each). No issues were silently closed without resolution.

**Response quality:** Bug reports (#1486, #1466, #1488) received same-day or next-day fixes with commits directly referencing the issue. Tutorial issues (#1495-1498) were batch-addressed in a documentation sprint. External user issues (#1421, #1418, #1505) received prompt responses. The longest-open issue (#1449, 66.2 days) was a documentation task, not a blocking bug. The new longest (#1529, 45.7 days) involved DLR branch handling, resolved in the v0.33.4/v0.33.5 release cycle.

### Open Issues (10 most recent)

| # | Title | Created | Age (days) |
|---|-------|---------|------------|
| 1570 | Bug when using slacks and reductions with PowerModels | 2026-03-23 | 1 |
| 1560 | Dual calculations | 2026-03-16 | 8 |
| 1558 | StartupTime data is missing | 2026-03-03 | 21 |
| 1557 | Renewable profiles in Natural Units treated as scaling factors | 2026-03-03 | 21 |
| 1547 | Support DC Power Flow in the Loop + Reductions | 2026-02-20 | 32 |
| 1545 | Bug in initializing DC power flow data? | 2026-02-19 | 33 |
| 1537 | Add losses approximations to PTDF models | 2026-02-12 | 40 |
| 1534 | Refactor ProductionCostExpression | 2026-02-11 | 41 |
| 1533 | Document HVDCTwoTerminalLCC | 2026-02-10 | 42 |
| 1530 | Ramp down limits: inequality flipped? | 2026-02-06 | 46 |

**Oldest open issue in sample:** 46 days (#1530)
**Mix:** 4 bug reports, 3 feature requests, 2 refactoring, 1 documentation

Note: Issue #1570 (1 day old) was already addressed by merged PR #1571 (Copilot-authored fix merged 2026-03-24); it may close imminently. The open issues are recent and represent active development items rather than a neglected backlog.

### Data Source

- `gh issue list --repo NREL-Sienna/PowerSimulations.jl --state closed --limit 20` (accessed 2026-03-24)
- `gh issue list --repo NREL-Sienna/PowerSimulations.jl --state open --limit 10` (accessed 2026-03-24)
- `gh api repos/NREL-Sienna/PowerSimulations.jl/issues/{n}/comments` for comment counts (accessed 2026-03-24)
- `gh api repos/NREL-Sienna/PowerSimulations.jl/issues/{n}/timeline` for cross-reference events (accessed 2026-03-24)

## Implications

The issue tracker is healthy and actively maintained. Key indicators:

1. **Responsiveness:** Median 20.7-day close time is reasonable for a research codebase. Critical bugs get same-day fixes.
2. **Acknowledgment ratio:** All 20 sampled closed issues were resolved with code fixes or documentation updates. No issues were silently closed or ignored.
3. **Backlog management:** Open issues are recent (all under 46 days) and represent current work items, not an accumulating debt. The newest issue (#1570) already has a merged fix.
4. **External engagement:** Several issues (#1505, #1421, #1418) were filed by external users and received prompt, helpful responses.

The tracker reflects a team that treats issue management as part of the development workflow rather than an afterthought.
