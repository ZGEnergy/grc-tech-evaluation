---
test_id: E-2
tool: gridcal
dimension: maturity
network: N/A
protocol_version: "v11"
skill_version: v2
test_hash: "060ee3ca"
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

# E-2: Commit Activity

## Result: INFORMATIONAL

## Finding

The repository shows very high commit activity with approximately 2,217 commits in the last 12 months across 12 unique committers (excluding bots). Development is heavily concentrated on the lead developer (SanPen, 56.9%) with a secondary cluster of eRoots Analytics employees. A significant portion of commits (231, 10.4%) have null authors, indicating bulk merges from the private eRoots development repository.

## Evidence

**Commit volume (2025-03-24 to 2026-03-24, via GitHub API paginated query):**
- Total commits: **2,217** (22 full pages of 100 + 17 on final page)

**Unique committers (last 12 months, GitHub API):**

| Rank | Author | Commits | Share | Affiliation |
|------|--------|---------|-------|-------------|
| 1 | SanPen | 1,261 | 56.9% | Creator/Lead, eRoots |
| 2 | alexblancoeroots | 280 | 12.6% | eRoots developer |
| 3 | (null/email-only) | 231 | 10.4% | Bulk merge commits |
| 4 | JosepFanals | 209 | 9.4% | eRoots contributor |
| 5 | Carlos-Alegre | 112 | 5.1% | eRoots contributor |
| 6 | mmutto | 54 | 2.4% | eRoots developer |
| 7 | leeraiyan | 28 | 1.3% | Contributor |
| 8 | mrosesgh | 24 | 1.1% | eRoots developer |
| 9 | dependabot[bot] | 8 | 0.4% | Bot |
| 10 | fernpos | 6 | 0.3% | Contributor |
| 11 | ramferan | 2 | 0.1% | Contributor |
| 12 | PabloDJ | 2 | 0.1% | Contributor |

**Total unique human committers:** 11 (excluding dependabot bot).

**Substantive vs maintenance ratio:**
- Dependabot commits: 8 (0.4%) -- pure maintenance (dependency updates)
- Null-author bulk merges: 231 (10.4%) -- consolidated feature/bugfix work from private repo
- Named human commits: 1,978 (89.2%) -- mix of features, bug fixes, refactoring
- Estimated substantive ratio: ~90% substantive, ~10% maintenance/dependency

**Dual-repo development model:** The 231 null-author commits represent periodic bulk merges from the private eRoots development repository. This means the public GitHub commit history undercounts the actual development pace and obscures individual commit attribution for a significant fraction of work.

Sources:
- GitHub API: `repos/SanPen/GridCal/commits?since=2025-03-24T00:00:00Z&until=2026-03-24T00:00:00Z` (paginated, accessed 2026-03-24)

## Implications

The commit volume (2,217/year) is very high for a power systems tool, indicating sustained active development. However, the dual-repo model makes external audit of individual changes difficult. The concentration of commits among eRoots employees (SanPen + alexblancoeroots + JosepFanals + Carlos-Alegre + mmutto + mrosesgh = ~86%) means the project's development velocity is directly tied to eRoots Analytics' staffing and commercial viability.
