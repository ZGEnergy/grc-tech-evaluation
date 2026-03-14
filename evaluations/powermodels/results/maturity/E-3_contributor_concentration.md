---
test_id: E-3
tool: powermodels
dimension: maturity
network: N/A
status: fail
workaround_class: null
timestamp: 2026-03-13T00:00:00Z
protocol_version: v10
skill_version: v1
test_hash: "622d8ddd"
---

# E-3: contributor_concentration

## Finding

Lifetime commit concentration is extreme: @ccoffrin (LANL) accounts for 82.9% of all commits (831 of 1002). The bus factor for the core domain knowledge is 1. Reviewer concentration is low by formal approval count but the informal review model (code comments + direct merges) means @odow and @ccoffrin jointly gatekeep all substantive changes.

## Evidence

### Commit Concentration

Lifetime commit data via `gh api repos/lanl-ansi/PowerModels.jl/contributors`:

| Contributor | Commits | % of Total |
|-------------|---------|------------|
| ccoffrin | 831 | 82.9% |
| pseudocubic | 45 | 4.5% |
| jd-lara | 34 | 3.4% |
| odow | 22 | 2.2% |
| rb004f | 15 | 1.5% |
| (others) | 55 | 5.5% |
| **Total** | **1002** | 100% |

**Top contributor commit %:** 82.9% (@ccoffrin)
**Top 3 combined:** 90.8% (ccoffrin + pseudocubic + jd-lara)
**Bus factor:** 1 — @ccoffrin holds the domain expertise; no other contributor comes close on core formulation code

Note: The last 12 months show @ccoffrin with 0 direct commits, @odow driving 17 of 24. The "bus factor" for ongoing maintenance has partially transferred, but the intellectual history is concentrated in one person.

### Reviewer Concentration

Sample: last 50 merged PRs queried via `gh pr list --repo lanl-ansi/PowerModels.jl --state merged --limit 50`.

Review data obtained from `gh api repos/lanl-ansi/PowerModels.jl/pulls/{number}/reviews` for all 50 PRs:

- **PRs with formal GitHub reviews:** 16 of 50 (34 PRs merged without formal GitHub review — typical for self-merges by maintainers or trivial bot/CI PRs)
- **Total non-bot formal approvals:** 4
- **Top reviewer by approvals:** odow — 4 of 4 approvals (100%)
- **Top reviewer by total review comments:** ccoffrin — 12 total review comments (non-approval); odow — 23; mtanneau — 9

Bots excluded (dependabot[bot] authored several PRs but had no reviews).

**Top reviewer approval %:** odow — 100% of formal approvals (4/4)
**Top 3 combined approval %:** odow (100%) — only one reviewer formally approved any PR in this sample

**Methodology note:** The PowerModels.jl project does not rely heavily on the formal GitHub "Approve" review state. Most PRs from @odow are self-merged after informal discussion in issue threads or PR comments. The low formal approval count reflects workflow norms rather than lack of oversight. However, this means the review process is not externally auditable.

**Concentration flag:** Yes — top single reviewer accounts for 100% of formal approvals in 50-PR sample.

## Implications

The extreme lifetime commit concentration (82.9% from one person) and the informal, non-auditable review process both represent maturity risks. The effective bus factor is 1 on core domain knowledge. While @odow's involvement provides JuMP-level engineering quality, power systems domain expertise is concentrated in @ccoffrin. If @ccoffrin disengages, the project could drift toward a pure JuMP compatibility maintenance mode with no active power systems expert. This is a fail on the contributor concentration criterion.
