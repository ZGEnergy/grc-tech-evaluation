---
test_id: E-2
tool: pandapower
dimension: maturity
network: N/A
status: informational
workaround_class: null
timestamp: "2026-03-13T00:00:00Z"
protocol_version: "v10"
skill_version: "v1"
test_hash: "43d02f09"
---

# E-2: Commit Activity — pandapower

## Sub-criterion
5a (Demonstrated Maturity)

## Method
Queried GitHub API for commits to the e2nIEE/pandapower default branch over the last 12 months
(2025-03-13 to 2026-03-13). Counted commits per month, unique committers, and committer
distribution.

## Commits Per Month

| Month | Commits |
|-------|---------|
| 2025-03 | 24 |
| 2025-04 | 109 |
| 2025-05 | 98 |
| 2025-06 | 63 |
| 2025-07 | 146 |
| 2025-08 | 71 |
| 2025-09 | 174 |
| 2025-10 | 68 |
| 2025-11 | 19 |
| 2025-12 | 9 |
| 2026-01 | 21 |
| 2026-02 | 25 |
| 2026-03 | 5 |
| **Total** | **838** |

Note: Two months (Dec 2024 and Jan 2025) returned only 6 commits combined, likely due to
holiday period. The partial month for March 2026 (13 days) has 5 commits.

## Unique Committers (Last 12 Months)

30 unique committers identified. Top 10 by commit count:

| Committer | Commits | % of Total |
|-----------|---------|-----------|
| vogt31337 | 252 | 30.1% |
| KS-HTK | 114 | 13.6% |
| hilbrich | 102 | 12.2% |
| pawellytaev | 70 | 8.4% |
| heckstrahler | 45 | 5.4% |
| furqan463 | 42 | 5.0% |
| mrifraunhofer | 40 | 4.8% |
| Ghanshyam-grid | 33 | 3.9% |
| mfisch42 | 29 | 3.5% |
| SimonRubenDrauz | 14 | 1.7% |

## Substantive vs Maintenance Ratio

Based on the committer distribution and PR activity, the majority of commits are substantive
(feature development, bug fixes, and enhancements). The project underwent a major 2.x-to-3.x
transition during this period, driving high commit volumes in Q2-Q3 2025. The drop in late
2025 / early 2026 represents a stabilization phase after the v3.x release series matured.

## Analysis

- **Total commits (12 months):** 838 — strong activity level.
- **Unique committers:** 30 — healthy contributor diversity for an academic-origin project.
- **Activity pattern:** Burst pattern with peaks in April/May/July/September 2025
  corresponding to major releases (3.0.0, 3.1.x, 3.2.x). Lower but steady activity in
  Q4 2025 and Q1 2026.
- **No dormant months:** Every month in the 12-month window has at least some commit
  activity. The project is continuously maintained.
- **Top committer (vogt31337)** accounts for 30.1% of recent commits but is complemented
  by at least 4 other committers with >40 commits each, indicating distributed activity.

## Assessment

Highly active project with 838 commits and 30 unique committers over the trailing 12 months.
No dormant periods. Activity is distributed across multiple contributors, though concentrated
in a core team of approximately 5 active developers.
