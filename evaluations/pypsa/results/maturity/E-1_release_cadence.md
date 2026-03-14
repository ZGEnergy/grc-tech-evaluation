---
test_id: E-1
tool: pypsa
dimension: maturity
network: N/A
status: pass
workaround_class: null
timestamp: 2026-03-13T12:00:00Z
protocol_version: v10
skill_version: v1
test_hash: 5748452f
---

# E-1: Release Cadence

## Findings

### Release Count (Last 24 Months: 2024-03-13 to 2026-03-13)

**33 releases** in the 24-month window, averaging 1.4 releases per month.

### Last Release

v1.1.2, published 2026-02-23 (18 days before evaluation date).

### Semver Compliance

All releases follow semantic versioning (MAJOR.MINOR.PATCH). The project
reached v1.0.0 on 2025-10-14, preceded by a release candidate (v1.0.0rc1
on 2025-08-15). The 0.x series used minor versions for breaking changes
and patch versions for fixes, consistent with pre-1.0 semver convention.

### Release Timeline (24-Month Window)

| Version Range | Period | Count |
|---------------|--------|-------|
| v1.1.x | 2026-02 | 3 |
| v1.0.x | 2025-10 to 2026-01 | 8 |
| v0.35.x | 2025-07 to 2025-08 | 3 |
| v0.34.x | 2025-03 to 2025-04 | 2 |
| v0.33.x | 2025-02 to 2025-03 | 3 |
| v0.32.x | 2024-12 to 2025-03 | 3 |
| v0.31.x | 2024-10 to 2024-11 | 3 |
| v0.30.x | 2024-08 to 2024-09 | 4 |
| v0.29.0 | 2024-07 | 1 |
| v0.28.0 | 2024-05 | 1 |
| v0.27.x | 2024-03 | 1 |

### Assessment

Excellent release cadence. The project is actively maintained with frequent
patch releases addressing bugs and compatibility issues (e.g., pandas 3.0
compatibility fixes in v1.0.6-v1.0.7). The v1.0.0 release marks a maturity
milestone with stable API commitments.

## Recorded Metrics

- release_count: 33 (24-month window)
- last_release_date: 2026-02-23
- versioning: semver (MAJOR.MINOR.PATCH), compliant
