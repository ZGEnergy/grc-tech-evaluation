---
test_id: E-5
tool: powersimulations
dimension: maturity
network: N/A
protocol_version: "v4"
status: informational
workaround_class: null
wall_clock_seconds: null
peak_memory_mb: null
loc: null
solver: null
timestamp: "2026-03-07T05:00:00Z"
---

# E-5: Issue Tracker Health

## Summary

The PowerSimulations.jl issue tracker shows **moderate activity with mixed responsiveness**. The maintainers close issues but with highly variable timelines. The median time-to-close is 66 days, but the distribution is bimodal: some issues are resolved within days while others linger for months or years.

## Repository Statistics

- **Open issues (total, including PRs):** 66
- **Stars:** 311
- **Forks:** 78

## Closed Issues Sample (Most Recently Updated)

| Issue | Created | Closed | Days | Title |
|-------|---------|--------|------|-------|
| #1546 | 2026-02-19 | 2026-03-02 | 10 | `Source` with time series? |
| #1531 | 2026-02-07 | 2026-02-13 | 5 | Market bid VOM cost missing `dt` multiplier |
| #1525 | 2026-01-27 | 2026-02-17 | 20 | PowerFlow HVDC Tracking issue |
| #1510 | 2026-01-08 | 2026-02-14 | 37 | Handling 3D Variables in Emulator |
| #1370 | 2025-09-09 | 2026-02-20 | 163 | 2D method refactoring |
| #1138 | 2024-09-03 | 2026-02-20 | 534 | Time-Varying parameters for MarketBidCost |
| #552 | 2020-11-18 | 2020-11-18 | 0 | TagBot trigger issue |

## Open Issues Sample (Most Recently Updated)

| Issue | Created | Comments | Labels | Title |
|-------|---------|----------|--------|-------|
| #1558 | 2026-03-03 | 0 | code bug | StartupTime data is missing |
| #1557 | 2026-03-03 | 0 | code bug | Renewable profiles Natural Units |
| #1554 | 2026-02-28 | 0 | code bug | _read_results emulator issue |
| #1545 | 2026-02-19 | 3 | code bug | Bug in DC power flow init |
| #1547 | 2026-02-20 | 0 | -- | DC Power Flow in Loop + Reductions |
| #1537 | 2026-02-12 | 0 | -- | Losses approximations to PTDF |
| #1534 | 2026-02-11 | 1 | -- | Refactor ProductionCostExpression |
| #1533 | 2026-02-10 | 0 | documentation | Document HVDCTwoTerminalLCC |
| #1530 | 2026-02-06 | 1 | -- | Ramp down limits: inequality flipped? |
| #1529 | 2026-02-05 | 0 | -- | Equivalent Line Rating for reduced branches |
| #1528 | 2026-02-03 | 0 | -- | Unused argument in `_add_pwl_constraint!` |
| #1491 | 2025-12-16 | 1 | feature request | Complete ShiftablePowerLoad formulation |

## Closure Time Statistics (Sample of 20 Most Recently Closed)

- **Median:** 66 days
- **Mean:** 163.5 days
- **Min:** 0 days
- **Max:** 1,026 days
- **Distribution:** [0, 5, 10, 20, 25, 27, 27, 27, 27, 37, 66, 97, 134, 135, 163, 198, 305, 407, 534, 1026]

## Observations

- **Bimodal closure pattern:** Quick fixes (0-27 days) vs. long-running issues (100-1000+ days). The 1,026-day outlier and 534-day issue suggest some issues are deprioritized but eventually addressed during major refactors.
- **Low external engagement:** Most issues appear to be filed by the core team themselves, with low comment counts on open issues. This is typical of a project with few external users relative to its internal development team.
- **Labels used sparingly:** Only "code bug", "feature request", and "documentation" labels are in use. No priority labels, milestones, or project boards observed.
- **Active triage:** Issues from early 2026 are being filed and addressed, showing the tracker is actively maintained.
- **Many open issues are self-filed enhancement/refactoring tasks** rather than external bug reports, which is a positive signal for code quality awareness.

## Source

- GitHub API: `repos/NREL-Sienna/PowerSimulations.jl/issues?state=closed&per_page=20`
- GitHub API: `repos/NREL-Sienna/PowerSimulations.jl/issues?state=open&per_page=15`
