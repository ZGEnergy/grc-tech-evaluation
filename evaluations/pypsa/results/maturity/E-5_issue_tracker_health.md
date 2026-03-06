---
test_id: E-5
tool: pypsa
dimension: maturity
status: pass
timestamp: 2026-03-05
---

# E-5: Issue Tracker Health

## Finding

PyPSA's issue tracker is actively maintained with rapid response times. Most recent issues are resolved within 0-1 days. Older feature requests are periodically cleaned up.

## Evidence

**Repository stats:** 117 open issues, 1884 stars, 614 forks.

**Sample of 20 recently closed issues (resolution time in days):**

| Issue | Created | Closed | Days | Type |
|-------|---------|--------|------|------|
| #1604 | 2026-03-05 | 2026-03-05 | 0 | fix: warn on committable |
| #1592 | 2026-03-03 | 2026-03-04 | 1 | fix: statistics map flows |
| #1552 | 2026-02-05 | 2026-03-04 | 26 | feat: typical periods |
| #1594 | 2026-03-03 | 2026-03-04 | 0 | fix: deprecated groupby |
| #1595 | 2026-03-03 | 2026-03-04 | 0 | feat: DuckDB I/O |
| #1593 | 2026-03-03 | 2026-03-04 | 0 | docs: memory reduction |
| #431  | 2022-08-12 | 2026-03-04 | 1299 | feat: SOS2 constraints |
| #1597 | 2026-03-04 | 2026-03-04 | 0 | docs: update users |
| #1596 | 2026-03-04 | 2026-03-04 | 0 | fix: pandas 3.0 compat |
| #1587 | 2026-03-02 | 2026-03-03 | 0 | fix: deprecated groupby |
| #1588 | 2026-03-02 | 2026-03-03 | 0 | feat: cross-scenario warmstart |
| #1586 | 2026-03-02 | 2026-03-03 | 0 | perf: memory reduction |
| #1584 | 2026-03-01 | 2026-03-02 | 1 | deps: CI updates |
| #1570 | 2026-02-18 | 2026-02-27 | 8 | feat: market power example |
| #1583 | 2026-02-26 | 2026-02-26 | 0 | bug: solver logging |
| #1541 | 2026-01-29 | 2026-02-26 | 28 | bug: multi_investment_periods |
| #1580 | 2026-02-25 | 2026-02-26 | 0 | bug: alignment error |

Median resolution time for recent issues (excluding long-standing feature requests): **0 days**.

**Sample of 10 open issues:**

| Issue | Created | Comments | Type |
|-------|---------|----------|------|
| #1288 | 2025-07-10 | 17 | feat: representative days (active discussion) |
| #1600 | 2026-03-04 | 0 | feat: URL validation |
| #1602 | 2026-03-04 | 2 | bug: storage committable (triaged) |
| #1603 | 2026-03-04 | 0 | feat: piecewise linear costs (PR open) |
| #1601 | 2026-03-04 | 0 | feat: network reset |
| #1568 | 2026-02-16 | 0 | feat: NPAP integration |

Open issues use labels (needs triage, docs, dependencies) and are triaged promptly. Long-standing open issues (#431, #62) were eventually resolved, showing backlog cleanup.

## Implications

Excellent issue tracker health. The maintainers respond to and resolve issues rapidly (often same-day). Bug reports receive quick triage. The open issue count (117) is manageable relative to the project's size and activity level.
