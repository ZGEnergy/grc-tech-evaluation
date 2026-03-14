---
test_id: E-1
tool: matpower
dimension: maturity
network: N/A
protocol_version: "v10"
skill_version: "v1"
test_hash: "c8829ec7"
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
solver: null
timestamp: 2026-03-14T00:00:00Z
---

# E-1: Release Cadence

## Result: INFORMATIONAL

## Finding

MATPOWER has had 2 stable releases in the last 24 months (8.0 in May 2024, 8.1 in July 2025), indicating roughly annual release cadence. Total of 6 releases on GitHub spanning 2017-2025. The project uses standard semantic versioning with occasional beta pre-releases.

## Evidence

GitHub releases (via `gh api repos/MATPOWER/matpower/releases --paginate`), accessed 2026-03-14:

| Tag | Name | Published |
|-----|------|-----------|
| 8.1 | MATPOWER 8.1 | 2025-07-13 |
| 8.0 | MATPOWER 8.0 | 2024-05-17 |
| 8.0b1 | MATPOWER 8.0b1 | 2022-12-23 |
| 7.1 | MATPOWER 7.1 | 2020-10-08 |
| 7.0 | MATPOWER 7.0 | 2019-06-21 |
| 7.0b1 | MATPOWER 7.0b1 | 2018-11-01 |

**Releases in last 24 months (since 2024-03-14):** 2 (8.0, 8.1)

**Last release date:** 2025-07-13 (8 months ago)

**Versioning scheme:** Semantic versioning (MAJOR.MINOR) with optional beta pre-releases (e.g., 8.0b1). No patch releases observed; fixes accumulate into the next minor release.

**Cadence pattern:** Historically slow (18-month gaps between 7.0 and 7.1, 4+ years between 7.1 and 8.0). The 8.0-to-8.1 gap of ~14 months is shorter, but the pattern is irregular. The 8.0 release was a major rewrite (MP-Core framework), which explains the long 7.1-to-8.0 gap.

## Implications

The release cadence is slow but improving. Two releases in 24 months is adequate for a mature, stable tool where breaking changes are rare. However, the lack of patch releases means bug fixes can take months to reach users. For a production deployment, this cadence means pinning to a stable release and accepting that fixes arrive on the next minor release cycle. The project's maturity and stability partially compensate for the slow cadence -- MATPOWER's core algorithms have been stable since the 1990s.
