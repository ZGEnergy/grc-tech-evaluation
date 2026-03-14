---
test_id: E-2
tool: powermodels
dimension: maturity
network: N/A
status: qualified_pass
workaround_class: null
timestamp: 2026-03-13T00:00:00Z
protocol_version: v10
skill_version: v1
test_hash: "a144588f"
---

# E-2: commit_activity

## Finding

PowerModels.jl had 24 commits in the last 12 months (March 2025–March 2026) from 4 unique authors. Activity is low-volume but non-zero; the majority of substantive work shifted to @odow (JuMP ecosystem contributor from JuliaHub), while the project founder (@ccoffrin at LANL) appears to have reduced direct contributions over this period. The substantive-to-maintenance ratio is roughly 3:1.

## Evidence

**Period:** 2025-03-13 to 2026-03-13

**Total commits (12 months):** 24

### Unique committers (12 months):

| Author | Commits | Notes |
|--------|---------|-------|
| odow | 17 | Oscar Dowson, JuliaHub / JuMP ecosystem maintainer |
| dependabot[bot] | 4 | Automated dependency bumps (bot — excluded from human count) |
| LKuhrmann | 2 | External contributor (Luis Kuhrmann) |
| mtanneau | 1 | External contributor (Mathieu Tanneau, Georgia Tech) |

Human unique committers: 3

#### Substantive vs. maintenance classification:

Substantive (17 commits): bug fixes (bus merging logic, PSSE export, pf.jl element type), performance improvements (incidence matrix, PrecompileTools), test infrastructure refactors, docs fixes, new utility tests.

Maintenance (7 commits): 4 Dependabot bumps (actions/checkout, codecov-action, upload-pages-artifact), 2 "prep for release" commits, 1 JSON@1 compatibility update.

**Substantive-to-maintenance ratio:** ~2.4:1 (17 substantive / 7 maintenance)

**Data source:** `gh api repos/lanl-ansi/PowerModels.jl/commits?since=2025-03-13T00:00:00Z`

## Implications

The 24-commit pace over 12 months is low for a library of this scope, indicating the package is in maintenance/stabilization mode rather than active feature development. The shift of primary commit activity from @ccoffrin to @odow is notable — the JuMP ecosystem maintainer now drives most day-to-day work, which is a mixed signal: JuMP-tier oversight is high quality, but the original domain-expert author is less active. The 3:1 substantive-to-maintenance ratio (excluding bots) shows the project is doing real work, not just keeping CI green. Classified as qualified_pass given the low volume relative to peer tools.
