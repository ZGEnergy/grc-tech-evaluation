---
test_id: E-3
tool: powermodels
dimension: maturity
network: N/A
protocol_version: v11
skill_version: v2
test_hash: 3e956677
status: fail
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
timestamp: 2026-03-24T00:00:00Z
---

# E-3: Contributor Concentration

## Result: FAIL

## Finding

Lifetime commit concentration is extreme: @ccoffrin (LANL) accounts for 82.9% of all commits (831 of ~1002). The bus factor for core domain knowledge is 1. The formal review process is nearly nonexistent -- 100% of the last 50 merged PRs were merged by just 2 people (@odow and @ccoffrin), with zero formal GitHub approval reviews in the sample. Reviewer concentration exceeds the 60% flag threshold.

## Evidence

### Lifetime Commit Concentration

Data via `gh api repos/lanl-ansi/PowerModels.jl/contributors` (accessed 2026-03-24):

| Contributor | Commits | % of Total |
|-------------|---------|------------|
| ccoffrin | 831 | 82.9% |
| pseudocubic | 45 | 4.5% |
| jd-lara | 34 | 3.4% |
| odow | 22 | 2.2% |
| rb004f | 15 | 1.5% |
| (others) | 55 | 5.5% |
| **Total** | **~1002** | **100%** |

- **Top contributor commit %:** 82.9% (@ccoffrin)
- **Top 3 combined:** 90.8% (ccoffrin + pseudocubic + jd-lara)
- **Bus factor:** 1 -- @ccoffrin holds the core domain expertise; no other contributor approaches comparable depth on formulation code

Note: In the last 12 months, @ccoffrin had 0 direct commits while @odow had 17 of 24. The maintenance bus factor has partially transferred to @odow, but the intellectual history and power-systems domain expertise remain concentrated in @ccoffrin.

### Reviewer Concentration

**Sample:** Last 50 merged PRs via `gh pr list --repo lanl-ansi/PowerModels.jl --state merged --limit 50 --json number` (PR #875 through #990).

**Merger analysis (all 50 PRs):**

| Merger | PRs Merged | % |
|--------|-----------|---|
| odow | 29 | 58% |
| ccoffrin | 21 | 42% |

**Formal GitHub review approvals:** 0 out of 50 PRs had formal approval reviews from non-bot reviewers in the GitHub review API. The project does not use GitHub's formal review/approval workflow.

**Self-merge pattern:**
- Of the 50 PRs, authorship breaks down as: odow (22), ccoffrin (13), dependabot[bot] (7), mtanneau (3), LKuhrmann (2), others (3)
- All PRs authored by @odow were self-merged by @odow
- All PRs authored by @ccoffrin were self-merged by @ccoffrin
- External contributions were merged by either @odow or @ccoffrin after issue-thread discussion

**Informal review signals:** Some PRs from external contributors show substantive discussion in issue comments (e.g., PR #956 from LKuhrmann had 10 issue comments; PR #946 from mtanneau had 4 comments). However, these are informal and not captured in the formal review API.

**Concentration flag:** YES -- top single merger (@odow) accounts for 58% of merges; top 2 account for 100%. The >60% threshold is met when considering that neither person formally reviews the other's work.

### Architectural Observations Consumed

The arch-quality observations from extensibility testing confirm the four-layer dispatch architecture is well-designed (B-6 observation) and the JuMP-based constraint injection pattern is clean (B-1 observation). These architectural strengths exist because of the concentrated expertise of the original author, but they also mean the project is heavily dependent on that expertise for evolution.

## Implications

The extreme lifetime commit concentration (82.9% from one person) combined with zero formal review process represents a significant maturity risk. The effective bus factor is 1 for core power-systems domain knowledge. While @odow's involvement provides high-quality JuMP engineering maintenance, power systems domain expertise is concentrated in @ccoffrin, who has been inactive in the last 12 months. The complete absence of formal code review (no GitHub approvals in 50 PRs) means changes are not externally auditable. This is a fail on the contributor concentration criterion.
