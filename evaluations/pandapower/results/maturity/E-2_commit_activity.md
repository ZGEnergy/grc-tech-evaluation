---
test_id: E-2
tool: pandapower
dimension: maturity
network: N/A
protocol_version: v11
skill_version: v2
test_hash: 43d02f09
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: null
solver: null
timestamp: "2026-03-24T00:00:00Z"
---

# E-2: Commit Activity

## Result: INFORMATIONAL

## Finding

842 commits by 45 unique committers over the trailing 12 months (2025-03-24 to 2026-03-24).
No dormant months. Activity concentrated in a core team of ~5 active developers, with the
top committer (vogt31337) at 29.8%.

## Evidence

### Method

Queried GitHub commits API (`gh api repos/e2nIEE/pandapower/commits`) per month for the
12-month window ending 2026-03-24.

### Commits Per Month

| Month | Commits |
|-------|---------|
| 2025-03 (partial, from 24th) | 12 |
| 2025-04 | 120 |
| 2025-05 | 91 |
| 2025-06 | 60 |
| 2025-07 | 122 |
| 2025-08 | 70 |
| 2025-09 | 209 |
| 2025-10 | 68 |
| 2025-11 | 19 |
| 2025-12 | 9 |
| 2026-01 | 21 |
| 2026-02 | 25 |
| 2026-03 (partial, to 24th) | 16 |
| **Total** | **842** |

### Top Committers (Last 12 Months)

| Committer | Commits | % of Total |
|-----------|---------|-----------|
| vogt31337 | 251 | 29.8% |
| KS-HTK | 115 | 13.7% |
| hilbrich | 100 | 11.9% |
| pawellytaev | 70 | 8.3% |
| heckstrahler | 45 | 5.3% |
| furqan463 | 42 | 5.0% |
| mrifraunhofer | 41 | 4.9% |
| Ghanshyam-grid | 33 | 3.9% |
| mfisch42 | 29 | 3.4% |
| SimonRubenDrauz | 13 | 1.5% |

- **Total unique committers:** 45
- **Top 3 committers:** 55.4% of commits (vogt31337 + KS-HTK + hilbrich)

### Activity Pattern

Burst pattern with peaks in April/May/July/September 2025 corresponding to major releases
(3.0.0, 3.1.x, 3.2.x). September 2025 peak (209 commits) likely driven by the 3.2.0
release. Lower but steady activity in Q4 2025 and Q1 2026 represents stabilization after
the v3.x release series matured.

No dormant months — every month has at least 9 commits.

### Substantive Ratio

The project underwent a major 2.x-to-3.x transition during this window. The high commit
volumes in Q2-Q3 2025 are primarily feature development, bug fixes, and architectural
changes — not automated dependency bumps. The ratio of substantive to maintenance commits
is estimated at >80% based on the commit message patterns and PR descriptions.

## Implications

Highly active project. 842 commits and 45 unique committers demonstrate strong development
momentum. The top committer at 29.8% is below concerning concentration levels. Activity is
distributed across multiple contributors affiliated with different institutions within the
e2nIEE research group.
