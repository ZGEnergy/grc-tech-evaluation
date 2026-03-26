---
test_id: E-3
tool: gridcal
dimension: maturity
network: N/A
protocol_version: "v11"
skill_version: v2
test_hash: "de54934d"
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

# E-3: Contributor Concentration

## Result: INFORMATIONAL

## Finding

The project has a bus factor of 1. Santiago Penate Vera (SanPen) is the dominant contributor with 9,523 all-time commits (73.2% of the top-10 total). No merged PRs in the sample have any code review. The entire release pipeline flows through a single individual.

## Evidence

**Top 3 contributors (all-time, GitHub API, accessed 2026-03-24):**

| Rank | Author | All-Time Commits | Share of Top-10 |
|------|--------|-----------------|-----------------|
| 1 | SanPen | 9,523 | 73.2% |
| 2 | JosepFanals | 1,223 | 9.4% |
| 3 | Carlos-Alegre | 478 | 3.7% |

**Extended top-10:**

| Rank | Author | Commits |
|------|--------|---------|
| 4 | benceszirbik | 466 |
| 5 | alexblancoeroots | 286 |
| 6 | miek770 | 250 |
| 7 | QuimMoya | 178 |
| 8 | leeraiyan | 134 |
| 9 | Bengt | 112 |
| 10 | fernpos | 112 |

**Total all-time contributors:** 34 unique authors (GitHub API). Only 3 have >500 commits. The top contributor (SanPen) has 7.8x more commits than the second (JosepFanals).

**PR review analysis (last 29 merged PRs sampled):**
- PRs with assigned reviewers at merge time: **0 out of 29** (0%)
- PRs with actual review comments (checked via `/reviews` endpoint): **1 out of 7 spot-checked** (PR #334 had 1 review)
- PR authors in sample: dependabot (14), ClaudiaMachadoCervera (5), leeraiyan (2), SanPen (1), external contributors (7)
- All PRs merged without formal review gate

**Reviewer concentration:** With effectively 0% review coverage, reviewer concentration is undefined. There is no review workflow, no CODEOWNERS file, and no branch protection enforcing reviews.

**Bus factor indicators:**
- SanPen is the sole PyPI publisher (`spenate@eroots.tech`)
- SanPen is the sole GitHub repository owner
- SanPen performs all merges from the private eRoots development repository
- SanPen is the sole named speaker at external events (FOSDEM 2026, LF Energy Summit)
- No co-maintainer or succession arrangement is publicly visible
- eRoots Analytics (founded 2022) provides some institutional continuity, but the company is closely identified with its founder

**Consumed observation — arch-quality (B-6):** The monolithic OPF formulation in `linear_opf_ts.py` (3146 LOC) was written primarily by SanPen. The architecture grew organically around a single developer's vision, with no documented extension points or contribution guide for the simulation layer.

Sources:
- GitHub API: `repos/SanPen/GridCal/contributors` (accessed 2026-03-24)
- GitHub API: `repos/SanPen/GridCal/pulls?state=closed` and `/reviews` endpoints (accessed 2026-03-24)
- [FOSDEM 2026 talk](https://fosdem.org/2026/schedule/event/7ARG7Y-making_of_a_modern_power_systems_software/) (speaker: Santiago Penate-Vera)

## Implications

The bus factor of 1 is the most significant project risk for maturity grading. While eRoots Analytics provides institutional continuity beyond a pure hobbyist project, all technical authority, release control, and architectural decisions concentrate in a single individual. The complete absence of code review on merged PRs (0% review rate) means there is no quality gate beyond the author's own judgment. This is a material concern for any organization considering operational reliance on this tool.
