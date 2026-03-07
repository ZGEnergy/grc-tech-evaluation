---
test_id: E-1
tool: matpower
dimension: maturity
network: N/A
protocol_version: "v4"
status: informational
workaround_class: null
timestamp: "2026-03-06T14:00:00Z"
---

# E-1: Release Cadence

## Data Source

GitHub Releases API: `gh api repos/MATPOWER/matpower/releases`

## Release History

| Version | Date | Type | Gap from Previous |
|---------|------|------|-------------------|
| 8.1 | 2025-07-13 | Stable | 14 months |
| 8.0 | 2024-05-17 | Stable (major) | 17 months |
| 8.0b1 | 2022-12-23 | Beta | 26 months |
| 7.1 | 2020-10-08 | Stable | 16 months |
| 7.0 | 2019-06-21 | Stable (major) | 8 months |
| 7.0b1 | 2018-11-01 | Beta | — |

## Last 24 Months (March 2024 — March 2026)

- **Releases in window: 2** (v8.0 in May 2024, v8.1 in July 2025)
- **Most recent release: v8.1** (2025-07-13) — 8 months ago
- **Versioning scheme:** Semantic-style (MAJOR.MINOR) with beta pre-releases

## Assessment

- **Cadence: Slow but steady.** Average 14-17 months between stable releases.
  This is typical for academic research software with a single primary developer.
- **No patch releases.** There are no 8.0.1-style bugfix releases; all fixes
  accumulate until the next minor/major release.
- **Beta releases precede majors.** v7.0b1 preceded v7.0 by 8 months; v8.0b1
  preceded v8.0 by 17 months.
- **v8.1 is a significant release.** Added HiGHS solver support, new mp.* OOP
  framework, three-phase power flow, and numerous bug fixes.
- **Active development continues.** Commits ongoing through February 2026,
  suggesting a future release is in preparation.

## Risk

The slow cadence means bugs discovered post-release may not be fixed for 12+
months. The lack of patch releases means users must either wait or apply fixes
from the `master` branch directly.
