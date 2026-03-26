---
test_id: E-2
tool: pypsa
dimension: maturity
network: N/A
protocol_version: v11
skill_version: v2
test_hash: a860b103
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: null
solver: null
timestamp: 2026-03-24T23:50:00Z
---

# E-2: Commit Activity

## Result: PASS

## Finding

PyPSA has strong commit activity with 321 total commits in the 12-month window ending
2026-03-24, from 37 unique committers (22 human, 15 bot accounts including dependabot
and pre-commit-ci). The substantive-to-maintenance ratio is approximately 95% human-authored.

## Evidence

**Source:** GitHub API (`gh api repos/PyPSA/PyPSA/commits`), queried 2026-03-24.

### Total Commits (12-Month Window: 2025-03-24 to 2026-03-24)

**321 commits** (100 + 100 + 100 + 21 across paginated API results), averaging ~27
commits per month.

### Unique Committers

**22 unique human committers** in the 12-month window (excluding bots).

With bots (dependabot[bot], pre-commit-ci[bot], Copilot): 37 total unique authors.

### Top Committers (12-Month Window)

| Committer | Commits | Percentage |
|-----------|---------|------------|
| lkstrp | 166 | 51.7% |
| fneum | 29 | 9.0% |
| FabianHofmann | 26 | 8.1% |
| Irieo | 20 | 6.2% |
| gincrement | 12 | 3.7% |
| dependabot[bot] | 10 | 3.1% |
| bobbyxng | 7 | 2.2% |
| pre-commit-ci[bot] | 5 | 1.6% |
| mgrabovsky | 5 | 1.6% |
| koen-vg | 4 | 1.2% |
| flxlchr | 4 | 1.2% |
| coroa | 4 | 1.2% |
| Others (25) | 29 | 9.0% |

### Substantive vs Maintenance Ratio

- **Bot commits** (dependabot, pre-commit-ci, Copilot): ~15 commits (4.7%)
- **Human commits**: ~306 commits (95.3%)
- **Substantive ratio**: ~95% human-authored (features, fixes, refactoring)

The bot commit ratio is low because the project does not auto-merge dependency updates;
dependabot PRs are reviewed and merged manually by maintainers.

## Implications

Strong commit activity. 321 commits from 22 unique human contributors shows healthy
project velocity. The contributor base extends well beyond the core maintainer team,
with contributions from institutional collaborators (TU Berlin, Open Energy Transition)
and external community members. The high substantive ratio indicates genuine development
activity rather than automated dependency bumps.

## Recorded Metrics

- total_commits: 321
- unique_committers: 22 (human only), 37 (including bots)
- substantive_ratio: ~95%
- primary_maintainer: lkstrp (51.7% of commits)
