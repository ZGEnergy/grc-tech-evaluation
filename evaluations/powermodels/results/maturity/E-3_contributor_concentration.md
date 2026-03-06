---
test_id: E-3
tool: powermodels
dimension: maturity
status: qualified_pass
timestamp: 2026-03-05
---

# E-3: Contributor Concentration

## Finding

PowerModels.jl has extreme contributor concentration. Carleton Coffrin (ccoffrin) accounts for 831 of ~1,010 total commits (82%). The top 3 contributors account for 910 commits (90%). Bus factor is effectively 1.

## Evidence

Top contributors by lifetime commits (from GitHub API):

| Rank | Author | Commits | % of Total |

|------|--------|---------|------------|

| 1 | ccoffrin (Carleton Coffrin, LANL) | 831 | 82.3% |

| 2 | pseudocubic | 45 | 4.5% |

| 3 | jd-lara (Jose Daniel Lara) | 34 | 3.4% |

| 4 | odow (Oscar Dowson) | 22 | 2.2% |

| 5 | rb004f | 15 | 1.5% |

Total contributors: 29 (GitHub reports).
Total commits: ~1,010.

Mitigating factor: odow has become the most active recent committer (19 of 37 commits in last 24 months), indicating some knowledge transfer to the JuMP ecosystem maintainer team. However, odow's contributions appear to be primarily CI/compatibility maintenance rather than core algorithm work.

Source: <https://github.com/lanl-ansi/PowerModels.jl> (contributors tab)

## Implications

The bus factor of 1 is a significant risk. If ccoffrin leaves LANL or shifts priorities, the project would lose its only deep domain expert. The recent activity from odow partially mitigates this for JuMP compatibility maintenance, but not for core power systems modeling logic. The 29 total contributors is reasonable for a niche academic tool but most are one-time contributors.
