---
test_id: E-3
tool: powersimulations
dimension: maturity
network: N/A
protocol_version: "v11"
skill_version: "v2"
test_hash: "3e956677"
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
timestamp: 2026-03-24T00:00:00Z
---

# E-3: Contributor & Reviewer Concentration

## Result: INFORMATIONAL

## Finding

Both commit authorship and review authority are heavily concentrated in a single individual (jd-lara / Jose Daniel Lara). He accounts for 69.5% of all-time commits and provided 81.4% of review approvals on the last 50 merged PRs. The bus factor is effectively 1. This is a significant sustainability risk despite the active contributor pool.

## Evidence

### Commit Concentration (Lifetime)

Total lifetime contributors tracked by GitHub: 20+ (API returns top contributors by commit count).

| Rank | Author | Commits | % |
|------|--------|---------|---|
| 1 | jd-lara | 7,548 | 69.5% |
| 2 | sourabhdalvi | 680 | 6.3% |
| 3 | claytonpbarrows | 577 | 5.3% |
| 4 | rodrigomha | 514 | 4.7% |
| 5 | daniel-thom | 401 | 3.7% |
| 6 | GabrielKS | 194 | 1.8% |
| 7 | Lilyhanig | 191 | 1.8% |
| 8 | m-bossart | 167 | 1.5% |
| 9 | SebastianManriqueM | 153 | 1.4% |
| 10 | kdheepak | 85 | 0.8% |

**Top contributor:** 69.5%
**Top 3 contributors:** 81.1%
**Bus factor:** 1 (jd-lara)

### Commit Concentration (Last 12 months)

In the last 12 months, jd-lara's share dropped to 40.7% — still the top contributor but with a broader active team (m-bossart 12.7%, SebastianManriqueM 9.9%, rodrigomha 9.7%, GabrielKS 9.5%, luke-kiernan 8.3%). This suggests the team is broadening, but institutional knowledge remains concentrated.

### Reviewer Concentration (Last 50 Merged PRs)

Of the 50 most recently merged PRs (spanning 2025-12-10 to 2026-03-24), 43 had at least one formal approval review. 7 PRs were merged without any recorded approval (PRs #1563, #1561, #1556, #1551, #1548, #1489, #1483).

| Reviewer | Approvals | % of reviewed PRs |
|----------|-----------|-------------------|
| jd-lara | 35 | 81.4% |
| daniel-thom | 3 | 7.0% |
| GabrielKS | 3 | 7.0% |
| rodrigomha | 2 | 4.7% |
| SebastianManriqueM | 2 | 4.7% |
| m-bossart | 2 | 4.7% |

**Top reviewer:** jd-lara at 81.4% (exceeds 60% threshold -- FLAGGED)
**Top 3 reviewers:** jd-lara + daniel-thom + GabrielKS = 95.3%
**PRs merged without review:** 7/50 (14%)

Of the 7 PRs merged without review, 4 were authored by Copilot bot (#1571, #1556, #1555, #1484 -- though #1571 and #1484 did receive approvals; only #1556 and #1516 are bot PRs without reviews). The remaining unreviewed PRs were authored by jd-lara (#1548, #1483) or other team members (#1563, #1561, #1551, #1489).

### Data Source

- `gh api repos/NREL-Sienna/PowerSimulations.jl/contributors?per_page=100` (accessed 2026-03-24)
- `gh api repos/NREL-Sienna/PowerSimulations.jl/pulls/{n}/reviews` for last 50 merged PRs (accessed 2026-03-24)

## Implications

**For Demonstrated Maturity:** The project has 20+ lifetime contributors and active development from 13 people in the last year, which is healthy for a research-oriented Julia package. The codebase is not a one-person hobby project — it has real team structure.

**For Sustainability Risk:** The concentration is a material risk. jd-lara is the sole gatekeeper for 81.4% of merged code (up from 78.3% in the prior audit 10 days ago). If this individual were to leave NREL or shift focus, there is no demonstrated second reviewer who could assume the review burden. The 14% of PRs merged without review approval further indicates that review discipline is informal rather than enforced. The recent trend toward broader commit distribution (40.7% vs 69.5% lifetime) is positive but does not yet extend to review authority.

**Bus factor = 1** is the key takeaway. The project would face a serious continuity challenge if jd-lara became unavailable, despite the growing contributor pool.
