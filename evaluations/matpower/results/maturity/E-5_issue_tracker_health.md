---
test_id: E-5
tool: matpower
dimension: maturity
network: N/A
protocol_version: "v4"
status: informational
workaround_class: null
timestamp: "2026-03-06T14:00:00Z"
---

# E-5: Issue Tracker Health

## Data Source

GitHub Issues API: `gh api repos/MATPOWER/matpower/issues?state=closed&per_page=20`
and `?state=open&per_page=10`

## Closed Issues (Last 20, sorted by updated date)

| # | Title | Created | Closed | Days Open | Comments |
|---|-------|---------|--------|-----------|----------|
| 277 | Add pretty-printing for buslink elements | 2025-11-11 | 2026-02-17 | 98 | 1 |
| 273 | t_qcqps_masters test | 2025-09-25 | 2026-02-16 | 144 | 2 |
| 278 | EV integration >533 bus error | 2025-11-25 | 2026-02-16 | 83 | 3 |
| 281 | Kundur 10-bar doesn't converge | 2026-01-05 | 2026-02-16 | 42 | 3 |
| 282 | loadxgendata absolute path bug | 2026-01-15 | 2026-02-16 | 32 | 2 |
| 283 | loadgenericdata absolute path | 2026-01-15 | 2026-02-16 | 32 | 1 |
| 276 | Jacobian computation question | 2025-10-28 | 2026-02-16 | 111 | 8 |
| 272 | Add cpf_example for uninstall | 2025-08-15 | 2026-02-16 | 185 | 2 |
| 271 | Uninstall doesn't remove examples/ | 2025-08-15 | 2026-02-16 | 185 | 0 |
| 280 | Kundur 10-bar (duplicate) | 2025-12-18 | 2026-01-05 | 18 | 0 |
| 275 | Fix DC OPF test for R2025b | 2025-09-26 | 2025-09-26 | 0 | 0 |
| 274 | DC OPF test failure linprog | 2025-09-25 | 2025-09-26 | 1 | 0 |
| 270 | test_matpower optimstatus field | 2025-08-05 | 2025-08-15 | 10 | 2 |
| 237 | Extended OPF example | 2024-07-01 | 2025-07-08 | 372 | 1 |
| 231 | OPF on radial system | 2024-04-30 | 2025-07-08 | 434 | 4 |
| 230 | Wind forecasting scenarios | 2024-04-09 | 2025-07-08 | 455 | 5 |
| 242 | Singular matrix warning | 2024-08-06 | 2025-07-08 | 336 | 1 |
| 199 | Australian 59-bus system | 2023-08-17 | 2025-07-05 | 688 | 4 |
| 267 | Update save2psse | 2025-05-13 | 2025-07-04 | 52 | 1 |
| 244 | New case1197.m | 2024-08-19 | 2025-07-04 | 319 | 4 |

## Open Issues (Last 10 by update)

| # | Title | Created | Age (days) |
|---|-------|---------|------------|
| 279 | CPF stuck in while loop | 2025-12-01 | 95 |
| 269 | Update to mp.opt_model | 2025-06-16 | 263 |
| 263 | Schema | 2025-04-27 | 313 |
| 136 | Distributed slack bus PF | 2022-01-07 | 1519 |
| 262 | Bus distance | 2025-03-12 | 359 |
| 246 | AC sensitivity analysis | 2024-09-11 | 541 |
| 233 | Multiple/distributed slack | 2024-05-30 | 645 |
| 178 | Overloaded branches alert | 2023-04-25 | 1046 |
| 127 | makePTDF ext2int error | 2021-09-24 | 1624 |
| 95 | Graphical load flow | 2020-04-07 | 2160 |

Total open issues: 16

## Metrics

| Metric | Value |
|--------|-------|
| Median time-to-close (last 20) | 108 days |
| Fastest close | 0 days (#275 — same-day fix) |
| Slowest close | 688 days (#199) |
| Oldest open issue | #95 (2020-04-07, 2160 days) |
| Median open issue age | 541 days |
| Average comments on closed issues | 1.9 |

## Response Pattern

Issues are typically closed in **batches** coinciding with releases:
- 8 issues closed on 2026-02-16 (batch triage session)
- 6 issues closed around 2025-07-04-08 (v8.1 release cleanup)

This is consistent with a single-maintainer project where issue triage happens
periodically rather than continuously.

## Response Quality

- **Bug reports** receive prompt investigation when related to CI/test failures
  (e.g., #274, #275 — closed within 1 day).
- **Feature requests** (e.g., distributed slack #136, #233) remain open indefinitely
  with acknowledgment but no implementation timeline.
- **Questions** are answered helpfully (#276 received 8 comments with detailed
  technical explanation) but with variable latency.
- **External contributions** (PRs #267, #272, #277) are reviewed and merged,
  though sometimes with multi-month delay.

## Assessment

The issue tracker is functional but reflects single-maintainer constraints.
Response quality is high when engaged, but response latency is unpredictable
(0 days to 688+ days). Feature requests have no triage process or priority
system. The 16 open issues are manageable but include long-standing requests
(distributed slack, #136, open since 2022) that have been acknowledged but
not addressed.
