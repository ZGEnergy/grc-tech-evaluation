---
test_id: E-1
tool: gridcal
dimension: maturity
network: N/A
protocol_version: "v11"
skill_version: v2
test_hash: "7ebe8c63"
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: estimated
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

GridCal/VeraGrid has an exceptionally high release cadence with 69+ releases on the `veragridengine` PyPI package alone (since its creation in late 2025), plus 59+ releases under the legacy `gridcalengine` package in the preceding period. Combined, there have been well over 100 releases in the last 24 months.

## Evidence

**PyPI release counts (accessed 2026-03-24):**

| Package | Total Versions | Versions in Last 24 Months (since 2024-03-24) |
|---------|---------------|-----------------------------------------------|
| `gridcalengine` | 176 total (5.0.0a2 through 5.4.1) | ~59 (5.1.7 through 5.4.1) |
| `veragridengine` | 69 total (0.0.1 through 5.6.38) | 69 (all versions; package created late 2025) |
| **Combined** | **~128 in last 24 months** | — |

The package was renamed from `gridcalengine` to `veragridengine` at version 5.4.0 (February 2026) due to a trademark dispute. A final `gridcalengine` 5.4.1 was published as a compatibility redirect.

**Latest release:** `veragridengine` 5.6.38 (as of 2026-03-24).

**Installed version:** 5.6.28 (released 2026-02-25).

**Versioning scheme:** SemVer-like `MAJOR.MINOR.PATCH`. The 5.6.x series alone spans 39 releases (5.6.0 through 5.6.38). No pre-release tags are used on `veragridengine`, though `gridcalengine` had `5.3.0a1-a3` and `5.4.0b1-b2`.

**GitHub tagged releases:** Only 28 tagged releases on GitHub (most recent: 5.6.20, published 2026-02-02). The gap between GitHub tags and PyPI versions indicates most releases are pushed directly from the private eRoots development repository without formal release notes.

**Release cadence by minor version (veragridengine):**

| Minor Version | Release Count | Approximate Timeframe |
|---------------|--------------|----------------------|
| 5.4.x | 12 | Late 2025 |
| 5.5.x | 19 | Late 2025 - Early 2026 |
| 5.6.x | 38 | Feb - Mar 2026 |

**No changelogs accompany releases.** GitHub release notes exist only for tagged releases (5.6.20 mentions "countless bug fixes"). Commit messages for PyPI-only releases are often just the version number (e.g., "5.6.31", "stuff").

Sources:
- [PyPI veragridengine](https://pypi.org/simple/veragridengine/) (accessed 2026-03-24)
- [PyPI gridcalengine](https://pypi.org/simple/gridcalengine/) (accessed 2026-03-24)
- [GitHub SanPen/GridCal releases](https://github.com/SanPen/GridCal/releases) (accessed 2026-03-24)

## Implications

The release cadence is exceptionally high (~2+ releases per week), indicating active development but raising stability concerns. The absence of changelogs or release notes for most releases makes it difficult for downstream consumers to assess upgrade risk. The dual-repo model (private eRoots development repository with periodic PyPI pushes) means the public GitHub history does not capture the full development narrative. For maturity grading, the high cadence is a double-edged signal: it demonstrates active maintenance but also suggests the API surface may not be fully stabilized.
