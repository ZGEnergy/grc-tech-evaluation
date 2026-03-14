---
test_id: E-1
tool: gridcal
dimension: maturity
network: N/A
status: informational
workaround_class: null
protocol_version: "v10"
skill_version: v1
test_hash: "7ebe8c63"
timestamp: "2026-03-13T23:00:00Z"
---

# E-1: Release Cadence

## Finding

GridCal/VeraGrid has an extremely high release cadence with 209 combined PyPI releases across both package names in the last 24 months, averaging approximately 2 releases per week.

## Evidence

**PyPI package history (last 24 months, since 2024-03-13):**

| Package | Releases | Date Range |
|---------|----------|------------|
| `gridcalengine` | 143 | 2024-03-13 to 2026-02-02 (final release under old name) |
| `veragridengine` | 66 | 2025-08-27 to 2026-03-12 |
| **Combined total** | **209** | — |

Note: The package was renamed from `gridcalengine` to `veragridengine` at version 5.4.0 (August 2025). A final `gridcalengine` 5.4.1 was published on 2026-02-02 as a redirect/compatibility release.

**Latest release:** `veragridengine` 5.6.34, released 2026-03-12 (1 day before evaluation).

**Installed version:** 5.6.28, released 2026-02-25 (16 days behind latest).

**Versioning scheme:** SemVer-like `MAJOR.MINOR.PATCH` with rapid patch-level iteration. The 5.6.x series alone has 15 releases between 2026-02-02 and 2026-03-12. No pre-release tags are used on the `veragridengine` package (though `gridcalengine` had `5.4.0b1` and `5.4.0b2`).

**GitHub releases:** Only 28 tagged releases on GitHub (most recent: 5.6.20). The remaining PyPI releases are untagged, pushed directly from the private eRoots development repository.

**Release cadence breakdown (veragridengine only):**
- 2025 Q3 (Aug-Sep): 5 releases (initial package setup)
- 2025 Q4 (Oct-Dec): 23 releases
- 2026 Q1 (Jan-Mar): 22 releases (through 2026-03-12)

## Implications

The release cadence is very high, indicating active development but also potential stability concerns. The gap between GitHub-tagged releases (28) and PyPI releases (209 combined) suggests most releases are patch-level fixes pushed without formal release notes. The rapid iteration rate means any version pin may drift quickly, but the patch-level versioning suggests backward compatibility is maintained within minor versions.
