---
test_id: E-1
tool: pypsa
dimension: maturity
status: pass
timestamp: 2026-03-05
---

# E-1: Release Cadence (Last 24 Months)

## Finding

PyPSA maintains an aggressive release cadence with 20+ releases in the last 24 months, including a major v1.0.0 release in October 2025.

## Evidence

Releases from March 2024 to March 2026 (24-month window):

| Version | Date |
|---------|------|
| v1.1.2 | 2026-02-23 |
| v1.1.1 | 2026-02-23 |
| v1.1.0 | 2026-02-17 |
| v1.0.7 | 2026-01-13 |
| v1.0.6 | 2025-12-22 |
| v1.0.5 | 2025-12-04 |
| v1.0.4 | 2025-11-21 |
| v1.0.3 | 2025-11-06 |
| v1.0.2 | 2025-10-24 |
| v1.0.1 | 2025-10-20 |
| v1.0.0 | 2025-10-14 |
| v1.0.0rc1 | 2025-08-15 |
| v0.35.2 | 2025-08-15 |
| v0.35.1 | 2025-07-03 |
| v0.35.0 | 2025-06-22 |
| v0.34.1 | 2025-04-07 |
| v0.34.0 | 2025-03-25 |
| v0.33.2 | 2025-03-12 |
| v0.32.2 | 2025-03-12 |
| v0.33.1 | 2025-03-03 |
| v0.33.0 | 2025-02-06 |
| v0.32.1 | 2025-01-23 |
| v0.32.0 | 2024-12-05 |
| v0.31.2 | 2024-11-27 |
| v0.31.1 | 2024-11-01 |
| v0.31.0 | 2024-10-01 |
| v0.30.3 | 2024-09-24 |
| v0.30.2 | 2024-09-11 |
| v0.30.1 | 2024-09-09 |
| v0.30.0 | 2024-08-30 |

Total: ~30 releases in 24 months. Average cadence: roughly one release every 3-4 weeks. The v1.0.0 milestone shows the project reached a maturity inflection point.

Source: `gh api repos/PyPSA/PyPSA/releases --paginate`

## Implications

Exceptional release cadence. The project is under very active development with frequent patch, minor, and major releases. This demonstrates strong maintainer commitment and a healthy development cycle.
