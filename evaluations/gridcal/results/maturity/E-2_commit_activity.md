---
test_id: E-2
tool: gridcal
dimension: maturity
network: N/A
status: informational
workaround_class: null
protocol_version: "v10"
skill_version: v1
test_hash: "060ee3ca"
timestamp: "2026-03-13T23:00:00Z"
---

# E-2: Commit Activity

## Finding

The repository shows very high commit activity with approximately 2,357 commits in the last 52 weeks, but the activity is heavily concentrated on a single developer (SanPen) who accounts for 58% of public GitHub commits. The GitHub stats API reports 1,349 owner commits vs 2,357 total, suggesting substantial development occurs in a private eRoots repository with periodic bulk merges to the public repo.

## Evidence

**Last 12 months (2025-03-13 to 2026-03-13):**
- Total commits on GitHub: >1,200 (API returned 100+ per page across 20+ pages)
- GitHub participation stats (last 52 weeks): 2,357 total commits, 1,349 from owner

**Unique committers (last 12 months, public GitHub):**

| Author | Commits | Role |
|--------|---------|------|
| SanPen (Santiago Penate Vera) | 461 | Creator/Lead |
| alexblancoeroots | 118 | eRoots developer |
| mmutto | 40 | eRoots developer |
| mrosesgh | 24 | eRoots developer |
| Carlos-Alegre | 9 | Contributor |
| leeraiyan | 8 | Contributor |
| JosepFanals | 3 | Contributor |
| PabloDJ | 2 | Contributor |
| (null/unknown) | 135 | Bulk merge commits |

**Total unique committers:** 8 named individuals (+ 135 null-author commits from bulk merges).

**Substantive vs maintenance ratio:** The 135 null-author commits are bulk merges from the private eRoots repo, representing consolidated feature/bugfix work. Dependabot contributes ~35 PRs all-time but these are dependency update PRs. Estimated substantive ratio: ~85% substantive, ~15% maintenance/dependabot.

**Commit cadence:** Weekly commit counts in early 2026 show 0-4 commits per week on the public repo, but this undercounts actual development which occurs in the private eRoots repo and is periodically synchronized.

## Implications

The high commit volume is positive for active development, but the dual-repo model (private eRoots + public GitHub) makes it difficult to assess the true development pace. The public repo receives periodic large merges rather than continuous small commits, which complicates change tracking and code review visibility.
