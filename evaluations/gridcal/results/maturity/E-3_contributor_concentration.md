---
test_id: E-3
tool: gridcal
dimension: maturity
network: N/A
status: informational
workaround_class: null
protocol_version: "v10"
skill_version: v1
test_hash: "de54934d"
timestamp: "2026-03-13T23:00:00Z"
---

# E-3: Contributor Concentration

## Finding

The project has a bus factor of 1. Santiago Penate Vera (SanPen) is the sole maintainer with 6,071 all-time commits (70%+ of total). No PRs in the last 50 merged have any code review — all are merged without reviewer assignment.

## Evidence

**Top 3 contributors (all-time, from GitHub API):**

| Rank | Author | All-Time Commits | Share |
|------|--------|-----------------|-------|
| 1 | SanPen | 6,071 | 70.3% |
| 2 | JosepFanals | 811 | 9.4% |
| 3 | alexblancoeroots | 420 | 4.9% |

**Total all-time committers:** 34 unique authors, but only 5 have >100 commits. The top contributor (SanPen) has 14.5x more commits than the second (JosepFanals).

**eRoots team contributors:** Several contributors are eRoots Analytics employees (alexblancoeroots, mmutto, mrosesgh, Carlos-Alegre, JosepFanals, QuimMoya, cristinafray, ramferan, ManuelNvro, JanaSoler, fernpos, leeraiyan, benceszirbik). External contributors include Navitasoft developers (peterkulik-navitasoft, jozsefgorcs-navitasoft) and individual contributors.

**PR review analysis (last 50 merged PRs):**
- Sample: 30 merged PRs examined (oldest from 2023-11-27)
- PRs with assigned reviewers: **0 out of 30** (0%)
- All PRs were merged directly by the author or by SanPen without formal review
- PR authors include: dependabot (13), SanPen (1), ClaudiaMachadoCervera (5), leeraiyan (2), external contributors (9)
- No review workflow or branch protection is enforced

**Bus factor assessment:**
- SanPen is the sole PyPI publisher (`spenate@eroots.tech`)
- SanPen is the sole GitHub repo owner
- SanPen performs all merges from the private eRoots repo
- No succession plan or co-maintainer arrangement is visible

## Implications

The bus factor of 1 is a significant project risk. While eRoots Analytics provides institutional continuity, all technical decisions, releases, and PR merges flow through a single individual. The complete absence of code review on merged PRs means there is no quality gate beyond the author's own judgment. This is a material concern for operational reliance.
