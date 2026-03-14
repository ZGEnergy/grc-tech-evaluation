---
test_id: E-3
tool: matpower
dimension: maturity
network: N/A
protocol_version: "v10"
skill_version: "v1"
test_hash: "4bce2de3"
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

# E-3: Contributor Concentration

## Result: INFORMATIONAL

## Finding

MATPOWER has extreme contributor concentration. The top contributor (rdzman / Ray Zimmerman) accounts for 97.6% of all lifetime commits (2,557 of 2,620 total). The bus factor is effectively 1. PR review is almost entirely self-merged by the maintainer. This is the single largest maturity risk for the project.

## Evidence

### Lifetime contributor data

Via `gh api repos/MATPOWER/matpower/contributors --paginate`, accessed 2026-03-14:

| Rank | Contributor | Commits | % of Total |
|------|-------------|---------|------------|
| 1 | rdzman (Ray Zimmerman) | 2,557 | 97.6% |
| 2 | eranschweitzer | 17 | 0.6% |
| 3 | BaljaaSS | 9 | 0.3% |
| 3 | WilsonGV | 9 | 0.3% |
| 5 | rwl | 6 | 0.2% |
| 6 | determ1ne | 4 | 0.2% |
| 7-17 | (11 contributors) | 1-3 each | <0.1% each |

**Total lifetime contributors:** 17
**Top contributor percentage:** 97.6%
**Top 3 cumulative:** 98.5%
**Bus factor:** 1

### PR review concentration

Via `gh pr list --repo MATPOWER/matpower --state merged --limit 50`, accessed 2026-03-14:

Of the last 45 merged PRs (lifetime, as only 45 exist):
- Most PRs are merged by rdzman himself, with no separate reviewer
- External contributions (WilsonGV, yasirroni, paulsmoses, etc.) are merged by rdzman
- No evidence of a second reviewer or code review requirement on any PR
- The project does not enforce PR review policies; the maintainer has direct push access to master

**Reviewer concentration:** Effectively 100% -- rdzman is the sole gatekeeper for all code entering the repository.

### Recent activity (last 12 months)

In the last 12 months, WilsonGV (7 commits, 5.8%) is the only contributor with more than 1 commit besides rdzman. WilsonGV contributed 3-phase modeling features (tap ratio, shunt elements, pretty-printing), indicating a potential emerging contributor in a specific domain.

## Implications

The bus factor of 1 is the most significant maturity risk. Ray Zimmerman retired from Cornell in mid-2024 and moved to Power Analytics Software, Inc. (PAS) full-time. His December 2024 blog post acknowledges this risk and describes plans to expand the maintainer team, but as of March 2026, the contributor data does not yet show this diversification materializing. The project's December 2024 announcement stated plans to add "additional project owners and maintainers" within months, but 15 months later, rdzman still accounts for 87.6% of recent commits and 100% of review authority. For a production dependency, this concentration requires a contingency plan.
