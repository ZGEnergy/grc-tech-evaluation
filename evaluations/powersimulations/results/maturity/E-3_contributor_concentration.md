---
test_id: E-3
tool: powersimulations
dimension: maturity
network: N/A
protocol_version: "v10"
skill_version: "v1"
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
timestamp: 2026-03-14T00:00:00Z
---

# E-3: Contributor & Reviewer Concentration

## Result: INFORMATIONAL

## Finding

Both commit authorship and review authority are heavily concentrated in a single individual (jd-lara / Jose Daniel Lara). He accounts for 70.5% of all-time commits and provided 78% of review approvals on the last 50 merged PRs. The bus factor is effectively 1. This is a significant sustainability risk despite the active contributor pool.

## Evidence

### Commit Concentration (Lifetime)

Total lifetime commits: 10,698 across 39 contributors.

| Rank | Author | Commits | % |
|------|--------|---------|---|
| 1 | jd-lara | 7,537 | 70.5% |
| 2 | sourabhdalvi | 680 | 6.4% |
| 3 | claytonpbarrows | 577 | 5.4% |
| 4 | rodrigomha | 513 | 4.8% |
| 5 | daniel-thom | 401 | 3.7% |
| 6 | GabrielKS | 194 | 1.8% |
| 7 | Lilyhanig | 191 | 1.8% |
| 8 | m-bossart | 158 | 1.5% |
| 9 | SebastianManriqueM | 127 | 1.2% |
| 10 | kdheepak | 85 | 0.8% |

**Top contributor:** 70.5%
**Top 3 contributors:** 82.2%
**Bus factor:** 1 (jd-lara)

### Commit Concentration (Last 12 months)

In the last 12 months, jd-lara's share dropped to 39.2% — still the top contributor but with a broader active team (m-bossart 11.7%, rodrigomha 10.9%, SebastianManriqueM 10.5%, GabrielKS 9.7%). This suggests the team is broadening, but institutional knowledge remains concentrated.

### Reviewer Concentration (Last 50 Merged PRs)

Of the 50 most recently merged PRs, 43 had at least one formal approval review. 7 PRs were merged without any recorded approval (PRs #1556, #1551, #1548, #1489, #1483, #1468, #1455).

| Reviewer | Approvals | % of reviewed PRs |
|----------|-----------|-------------------|
| jd-lara | 36 | 78.3% |
| GabrielKS | 3 | 6.5% |
| rodrigomha | 2 | 4.3% |
| m-bossart | 2 | 4.3% |
| daniel-thom | 2 | 4.3% |
| SebastianManriqueM | 1 | 2.2% |

**Top reviewer:** jd-lara at 78.3% (exceeds 60% threshold)
**Top 3 reviewers:** jd-lara + GabrielKS + rodrigomha = 89.1%
**PRs merged without review:** 7/50 (14%)

### Data Source

- `gh api repos/NREL-Sienna/PowerSimulations.jl/contributors?per_page=100` (accessed 2026-03-14)
- `gh api repos/NREL-Sienna/PowerSimulations.jl/pulls/{n}/reviews` for last 50 merged PRs (accessed 2026-03-14)

## Implications

**For 5a (Demonstrated Maturity):** The project has 39 lifetime contributors and active development from ~12 people in the last year, which is healthy for a research-oriented Julia package. The codebase is not a one-person hobby project — it has real team structure.

**For 5b (Sustainability Risk):** The concentration is a material risk. jd-lara is the sole gatekeeper for 78% of merged code. If this individual were to leave NREL or shift focus, there is no demonstrated second reviewer who could assume the review burden. The 14% of PRs merged without review approval further indicates that review discipline is informal rather than enforced. The recent trend toward broader commit distribution (39% vs 70% lifetime) is positive but does not yet extend to review authority.

**Bus factor = 1** is the key takeaway. The project would face a serious continuity challenge if jd-lara became unavailable, despite the growing contributor pool.
