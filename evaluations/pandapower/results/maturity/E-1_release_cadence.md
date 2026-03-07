---
test_id: E-1
tool: pandapower
dimension: maturity
network: N/A
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: null
peak_memory_mb: null
loc: null
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# E-1: Release Cadence

## Result: PASS

## Finding

pandapower has maintained a strong release cadence over the last 24 months (March 2024 -- March 2026), publishing 15 releases across two major version lines. Releases follow semantic versioning. The v3.0.0 major release (March 2025) introduced breaking changes (kW-to-MW unit convention, sign convention updates).

## Evidence

Releases in the 24-month window (March 2024 -- March 2026), sourced from GitHub releases API on 2026-03-06:

| Version | Date | Notes |
|---------|------|-------|
| v3.4.0 | 2026-02-09 | Latest stable |
| v3.3.2 | 2026-01-15 | |
| v3.3.0 | 2025-12-16 | |
| v3.2.1 | 2025-10-27 | |
| v3.2.0 | 2025-10-08 | |
| v3.1.2 | 2025-06-16 | |
| v3.1.1 | 2025-05-26 | |
| v3.0.0 | 2025-03-06 | Major breaking release |
| v2.14.11 | 2024-08-07 | |
| v2.14.9 | 2024-06-26 | |
| v2.14.8 | 2024-06-19 | |
| v2.14.7 | 2024-06-14 | |
| v2.14.6 | 2024-04-02 | |
| v2.14.5 | 2024-03-28 | |
| v2.14.2 | 2024-03-27 | |

- **Total releases in 24 months:** 15
- **Average interval:** ~7 releases/year
- **Most recent release:** v3.4.0, 2026-02-09 (25 days before evaluation)
- **Semver compliance:** Yes -- major bump for breaking changes, minor/patch for features and fixes
- **Sources:** [GitHub Releases](https://github.com/e2nIEE/pandapower/releases), [PyPI](https://pypi.org/project/pandapower/)

## Implications

The release cadence is healthy and consistent. Roughly monthly releases in active periods, with a natural gap between the v2.x and v3.x lines during the major version transition. The project shows no signs of release stagnation.
