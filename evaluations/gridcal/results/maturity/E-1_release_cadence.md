---
test_id: E-1
tool: gridcal
dimension: maturity
network: N/A
protocol_version: "v4"
status: pass
workaround_class: null
timestamp: 2026-03-06T05:00:00Z
---

# E-1: Release Cadence

## Criteria

Evaluate the frequency, regularity, and recency of releases over the past 24 months.

## Result: PASS

GridCal has a very active release cadence with approximately 40+ PyPI releases and 10
GitHub releases in the last 24 months.

### Evidence

- **Version range (24 months)**: v5.0.2 (November 2023) through v5.6.30 (latest)
- **PyPI releases**: ~40+ releases, averaging roughly 1-2 releases per month
- **GitHub releases**: 10 tagged releases (subset of PyPI releases, major milestones)
- **Most recent release**: v5.6.30 (early 2026)
- **No extended gaps**: No period longer than ~6 weeks without a release

### Versioning

GridCal does not strictly follow semantic versioning. Minor and patch version bumps
sometimes include breaking API changes (e.g., the rename from GridCal to VeraGridEngine
happened within the v5.x line). Version numbers increment frequently, with patch
versions sometimes reaching high numbers (e.g., v5.6.28, v5.6.30).

### Assessment

The release cadence demonstrates an actively maintained project with rapid iteration.
The high frequency of releases indicates responsive bug fixing and feature development.
The lack of strict semver is a minor concern for downstream dependency management but
does not affect the maturity assessment for release activity.
