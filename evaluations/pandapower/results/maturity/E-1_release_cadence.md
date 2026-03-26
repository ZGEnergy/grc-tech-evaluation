---
test_id: E-1
tool: pandapower
dimension: maturity
network: N/A
protocol_version: v11
skill_version: v2
test_hash: 93a82d15
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

# E-1: Release Cadence

## Result: INFORMATIONAL

## Finding

19 releases in the 24-month window (March 2024 through March 2026), averaging one release
every 5 weeks. Fully semver-compliant. Multi-branch maintenance confirmed (v3.2.x and v3.3.x
backports released same day). Last release: v3.3.3 on 2026-03-13.

## Evidence

### Method

Queried GitHub releases API (`gh api repos/e2nIEE/pandapower/releases`) and cross-referenced
with PyPI. Data collected 2026-03-24.

### Release History (March 2024 -- March 2026)

| Version | Release Date | Category |
|---------|-------------|----------|
| 2.14.2 | 2024-03-27 | Patch |
| 2.14.5 | 2024-03-28 | Patch |
| 2.14.6 | 2024-04-02 | Patch |
| 2.14.7 | 2024-06-14 | Patch |
| 2.14.8 | 2024-06-19 | Patch |
| 2.14.9 | 2024-06-26 | Patch |
| 2.14.11 | 2024-08-07 | Patch (last 2.x) |
| 3.0.0 | 2025-03-06 | Major |
| 3.1.1 | 2025-05-26 | Minor |
| 3.1.2 | 2025-06-16 | Patch |
| 3.2.0 | 2025-10-08 | Minor |
| 3.2.1 | 2025-10-27 | Patch |
| 3.2.2 | 2026-03-13 | Patch (backport) |
| 3.3.0 | 2025-12-16 | Minor |
| 3.3.1 | 2026-01-15 | Patch |
| 3.3.2 | 2026-01-15 | Patch |
| 3.3.3 | 2026-03-13 | Patch |
| 3.4.0 | 2026-02-09 | Minor |

**Note:** v2.14.10 also released 2024-08-07 (same day as v2.14.11), bringing total to 19.

### Analysis

- **Release count:** 19 releases in 24 months (~1 every 5.3 weeks).
- **Last release:** 2026-03-13 (11 days ago at time of audit).
- **Semver compliance:** Fully compliant. Major bump from 2.x to 3.x in March 2025. Minor
  and patch increments follow semantic conventions consistently.
- **Multi-branch maintenance:** Two releases on 2026-03-13 (v3.2.2 and v3.3.3) confirm
  active backport maintenance of older release branches. This is a sign of production maturity.
- **Major version gap:** 7-month gap between last 2.x release (2024-08-07) and 3.0.0
  (2025-03-06) reflects pre-release development, not inactivity.
- **Post-3.0 cadence:** Approximately monthly releases since May 2025.

## Implications

Active and healthy release cadence. 19 releases in 24 months with consistent semver practices
and multi-branch maintenance indicates a project that treats releases as production artifacts,
not just snapshots. No extended dormant periods.
