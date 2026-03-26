---
test_id: E-2
tool: powermodels
dimension: maturity
network: N/A
protocol_version: v11
skill_version: v2
test_hash: a860b103
status: qualified_pass
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

# E-2: Commit Activity

## Result: QUALIFIED PASS

## Finding

PowerModels.jl had 24 commits in the last 12 months (2025-03-24 to 2026-03-24) from 3 unique human authors. Activity is low-volume but non-zero; the majority of substantive work comes from @odow (Oscar Dowson, JuMP ecosystem maintainer at JuliaHub), while the project founder (@ccoffrin at LANL) had zero direct commits in this period. The substantive-to-maintenance ratio is approximately 2.4:1.

## Evidence

**Period:** 2025-03-24 to 2026-03-24

**Total commits:** 24

### Unique committers (12 months)

| Author | Commits | Role |
|--------|---------|------|
| odow | 17 | Oscar Dowson, JuliaHub / JuMP ecosystem maintainer |
| dependabot[bot] | 4 | Automated dependency bumps (excluded from human count) |
| LKuhrmann | 2 | External contributor |
| mtanneau | 1 | External contributor (Mathieu Tanneau, Georgia Tech) |

**Human unique committers:** 3

### Commit classification

**Substantive commits (17):**
- Bug fixes: bus merging logic (#972, #956), PSSE export syntax (#941), pf.jl element type (#939)
- Performance: incidence matrix optimization (#946), PrecompileTools for TTFX (#967)
- Test infrastructure: refactor runtests.jl (#962, #965), relax test tolerance (#976)
- Documentation: calc_admittance_matrix_inv tests/docs (#970), fix doc build (#966), remove empty docstrings (#963)
- Code quality: clean up imports (#961), spelling fix with deprecation (#959), fix parse_file (#958), move deprecations (#964)
- Precompilation: silence Memento logger (#980)

**Maintenance commits (7):**
- 4 Dependabot bumps (actions/checkout v4->v5, v5->v6; upload-pages-artifact v3->v4; codecov-action v4->v5)
- 2 release prep commits (v0.21.4, v0.21.5)
- 1 JSON@1 compatibility update

**Substantive-to-maintenance ratio:** 2.4:1 (17/7)

**Data source:** `gh api repos/lanl-ansi/PowerModels.jl/commits?since=2025-03-24T00:00:00Z&until=2026-03-24T00:00:00Z` (accessed 2026-03-24)

## Implications

The 24-commit pace over 12 months is low for a library of this scope, indicating the package is in maintenance/stabilization mode rather than active feature development. The shift of primary commit activity from @ccoffrin (0 commits in 12 months) to @odow (17 commits) is a notable risk: while JuMP-tier engineering oversight is high quality, the original domain-expert author is disengaged from day-to-day development. The 2.4:1 substantive-to-maintenance ratio shows the project is doing real work, not just keeping CI green. Classified as qualified_pass given the low absolute volume and single-person dominance of recent activity.
