---
test_id: E-5
tool: pypsa
dimension: maturity
slug: issue_tracker_health
network: N/A
protocol_version: v4
status: informational
workaround_class: null
timestamp: 2026-03-06T12:00:00Z
---

# E-5: Issue Tracker Health

## Summary

| Metric | Value |
|--------|-------|
| Open issues (total) | 120 |
| Median time-to-close (sample of 20) | 21.1 hours (0.9 days) |
| Issues closed within 1 day | 11/20 (55%) |
| Issues closed within 7 days | 13/20 (65%) |
| Min time-to-close | 0.5 hours |
| Max time-to-close | 60,040 hours (long-standing feature requests) |

## Sample of 20 Recently Closed Issues

| # | Title | Created | Closed | Time (hours) |
|---|-------|---------|--------|--------------|
| 1604 | fix: warn on committable=True for unsupported type | 2026-03-05 | 2026-03-05 | 2.5 |
| 1592 | Fix statistics map transmission flows | 2026-03-03 | 2026-03-04 | 31.8 |
| 1552 | Add typical periods agg method | 2026-02-05 | 2026-03-04 | 647.3 |
| 1594 | Fix deprecated groupby(axis=1) | 2026-03-03 | 2026-03-04 | 21.1 |
| 1595 | feat: add DuckDB as native I/O format | 2026-03-03 | 2026-03-04 | 20.6 |
| 1593 | docs: reduce peak memory in example | 2026-03-03 | 2026-03-04 | 20.4 |
| 431 | Endogenous technological learning with SOS2 | 2022-08-12 | 2026-03-04 | 30,500 |
| 1597 | Update users.md | 2026-03-04 | 2026-03-04 | 0.6 |
| 1596 | fix: Fix groupby() call for pandas 3.0 | 2026-03-04 | 2026-03-04 | 1.4 |
| 1587 | scigrid-redispatch example fix | 2026-03-02 | 2026-03-03 | 12.8 |
| 1588 | Feature: Cross-scenario warm-starting | 2026-03-02 | 2026-03-03 | 12.8 |
| 1586 | Scigrid-redispatch memory fix | 2026-03-02 | 2026-03-03 | 12.8 |
| 1584 | build(deps): bump github-actions | 2026-03-01 | 2026-03-02 | 29.9 |
| 549 | Adaption of multilink implementation | 2023-02-03 | 2025-12-18 | 24,984 |
| 1333 | Add processes components | 2025-08-15 | 2026-03-02 | 4,798 |
| 62 | Allow links to have a time delay | 2019-04-26 | 2026-03-02 | 60,040 |
| 1570 | Add example: market power model | 2026-02-18 | 2026-02-27 | 207.3 |
| 1583 | solve_model() multiple values error | 2026-02-26 | 2026-02-26 | 0.5 |
| 1541 | Error moving to PyPSA 1.0 | 2026-01-29 | 2026-02-26 | 672.9 |
| 1580 | Alignment Error with Storage-units | 2026-02-25 | 2026-02-26 | 16.4 |

## Sample of 10 Open Issues

| # | Title | Created | Comments | Age (days) |
|---|-------|---------|----------|-----------|
| 1607 | ConsistencyError on p_min_pu = p_max_pu | 2026-03-06 | 0 | 0 |
| 1606 | network.merge() adds default values for outputs | 2026-03-06 | 0 | 0 |
| 1605 | statistics on NetworkCollection not working | 2026-03-06 | 1 | 0 |
| 1602 | StorageUnit committable crash | 2026-03-04 | 2 | 2 |
| 1601 | Add function to reset network | 2026-03-04 | 0 | 2 |
| 1600 | Add URL validation | 2026-03-04 | 0 | 2 |
| 1591 | Deprecate get_strongly_meshed_buses | 2026-03-03 | 0 | 3 |
| 1490 | Add robustness requirements (EENS, LOLP) | 2025-12-11 | 1 | 85 |
| 1475 | Examples for subsidies, penalties, CfDs, PPAs | 2025-12-10 | 2 | 86 |
| 1288 | Implement Kotzur method for representative days | 2025-07-10 | 18 | 239 |

## Response Quality Assessment

**Bug reports** receive fast triage (typically same-day response from maintainers). Recent examples show bugs being fixed and released within hours (#1596: 1.4 hours, #1604: 2.5 hours).

**Feature requests** remain open longer but receive substantive discussion. Long-standing feature requests (#62, #431, #549) are eventually addressed, some after years of incremental development.

**Community PRs** are reviewed promptly -- external contributor PRs in the sample (#1588 warm-starting, #1595 DuckDB) were merged within 12-21 hours.

## Assessment

The issue tracker is healthy and actively maintained. The median time-to-close of 21 hours for recent issues indicates responsive maintenance. The 120 open issues is reasonable for a project of this size and maturity. Long-tail open items are primarily feature requests and enhancement proposals rather than unaddressed bugs.
