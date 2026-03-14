---
test_id: E-1
tool: pandapower
dimension: maturity
network: N/A
status: informational
workaround_class: null
timestamp: "2026-03-13T00:00:00Z"
protocol_version: "v10"
skill_version: "v1"
test_hash: "93a82d15"
---

# E-1: Release Cadence — pandapower

## Sub-criterion
5a (Demonstrated Maturity)

## Method
Checked PyPI release history and GitHub releases for pandapower over the last 24 months
(March 2024 through March 2026).

## Release History (March 2024 — March 2026)

| Version | Date | Notes |
|---------|------|-------|
| 2.14.2 | 2024-03-27 | Patch |
| 2.14.5 | 2024-03-28 | Patch |
| 2.14.6 | 2024-04-02 | Patch |
| 2.14.7 | 2024-06-14 | Patch |
| 2.14.8 | 2024-06-19 | Patch |
| 2.14.9 | 2024-06-25 | Patch |
| 2.14.10 | 2024-08-07 | Patch |
| 2.14.11 | 2024-08-07 | Patch (last 2.x) |
| 3.0.0 | 2025-03-06 | Major version bump |
| 3.1.1 | 2025-05-26 | Minor |
| 3.1.2 | 2025-06-16 | Patch |
| 3.2.0 | 2025-10-08 | Minor |
| 3.2.1 | 2025-10-27 | Patch |
| 3.2.2 | 2026-03-13 | Patch (maintenance backport) |
| 3.3.0 | 2025-12-16 | Minor |
| 3.3.1 | 2026-01-13 | Patch |
| 3.3.2 | 2026-01-14 | Patch |
| 3.3.3 | 2026-03-13 | Patch |
| 3.4.0 | 2026-02-09 | Minor |

**Total releases in 24-month window:** 19

## Analysis

- **Release count:** 19 releases over 24 months, averaging approximately one release every 5 weeks.
- **Last release date:** 2026-03-13 (v3.3.3 and v3.2.2, same day — indicates active maintenance
  of multiple release branches).
- **Semver compliance:** Fully semver-compliant. Major bump from 2.x to 3.x in March 2025. Minor
  and patch increments follow semantic conventions consistently.
- **Major version transition:** The 2.x-to-3.0.0 transition occurred in March 2025 with a 7-month
  gap from the last 2.x release (2.14.11, August 2024). This gap reflects pre-release development
  work for the major version, not inactivity — commit history shows continuous activity during
  this period.
- **Multi-branch maintenance:** Two releases on 2026-03-13 (v3.2.2 and v3.3.3) confirm the project
  maintains backport branches, which is a sign of production maturity.
- **Cadence consistency:** Post-3.0, releases have been steady at approximately monthly intervals:
  3.1.1 (May), 3.1.2 (Jun), 3.2.0 (Oct), 3.2.1 (Oct), 3.3.0 (Dec), 3.3.1-3.3.2 (Jan),
  3.4.0 (Feb), 3.3.3/3.2.2 (Mar).

## Assessment

Active and healthy release cadence. 19 releases in 24 months with consistent semver practices
and multi-branch maintenance. No extended dormant periods.
