---
test_id: E-1
tool: pypsa
dimension: maturity
network: N/A
protocol_version: v11
skill_version: v2
test_hash: 5748452f
status: pass
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
timestamp: 2026-03-24T23:50:00Z
---

# E-1: Release Cadence

## Result: PASS

## Finding

PyPSA has an excellent release cadence with 32 releases in the 24-month window ending
2026-03-24, averaging 1.3 releases per month. The most recent release (v1.1.2) was
published 2026-02-23, 29 days before this evaluation. All releases follow semantic
versioning.

## Evidence

**Source:** PyPI release history (https://pypi.org/project/pypsa/#history), accessed 2026-03-24.

### Release Count (24-Month Window: 2024-03-24 to 2026-03-24)

**32 releases**, averaging 1.3 releases per month.

### Last Release

v1.1.2, published 2026-02-23 (29 days before evaluation date).

### Semver Compliance

All releases follow semantic versioning (MAJOR.MINOR.PATCH). The project reached
v1.0.0 on 2025-10-14, preceded by a release candidate (v1.0.0rc1 on 2025-08-15).
The 0.x series used minor versions for breaking changes and patch versions for fixes,
consistent with pre-1.0 semver convention.

### Release Timeline (24-Month Window)

| Version Range | Period | Count |
|---------------|--------|-------|
| v1.1.x | 2026-02 | 3 |
| v1.0.x | 2025-10 to 2026-01 | 8 |
| v1.0.0rc1 | 2025-08 | 1 |
| v0.35.x | 2025-06 to 2025-08 | 3 |
| v0.34.x | 2025-03 to 2025-04 | 2 |
| v0.33.x | 2025-02 to 2025-03 | 3 |
| v0.32.x | 2024-12 to 2025-03 | 3 |
| v0.31.x | 2024-10 to 2024-11 | 3 |
| v0.30.x | 2024-08 to 2024-09 | 4 |
| v0.29.0 | 2024-07 | 1 |
| v0.28.0 | 2024-05 | 1 |

### Current PyPI Version

v1.1.2 (Development Status classifier: "5 - Production/Stable")

## Implications

Excellent release cadence. The project is actively maintained with frequent patch
releases addressing bugs and compatibility issues (e.g., pandas 3.0 compatibility
fixes in v1.0.6-v1.0.7). The v1.0.0 release marks a maturity milestone with stable
API commitments. The 32-release count in 24 months significantly exceeds the threshold
for a healthy open-source project.

## Recorded Metrics

- release_count: 32 (24-month window)
- last_release_date: 2026-02-23
- last_release_version: 1.1.2
- versioning: semver (MAJOR.MINOR.PATCH), compliant
