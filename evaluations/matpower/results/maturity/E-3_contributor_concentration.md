---
test_id: E-3
tool: matpower
dimension: maturity
network: N/A
protocol_version: "v4"
status: informational
workaround_class: null
timestamp: "2026-03-06T14:00:00Z"
---

# E-3: Contributor Concentration

## Data Source

GitHub Contributors API: `gh api repos/MATPOWER/matpower/contributors`

## Top Contributors (Lifetime)

| Rank | Contributor | Commits | % of Total |
|------|------------|---------|------------|
| 1 | rdzman (Ray Zimmerman) | 2,556 | 98.5% |
| 2 | eranschweitzer | 17 | 0.7% |
| 3 | BaljaaSS | 9 | 0.3% |
| 3 | WilsonGV | 9 | 0.3% |
| 5 | rwl | 6 | 0.2% |

**Total contributors: 17**
**Total commits: ~2,595**

## Bus Factor Analysis

Bus factor: 1

Ray Zimmerman (rdzman) accounts for 98.5% of all commits to the repository.
No other contributor has more than 17 commits (0.7%). This is the most extreme
contributor concentration of any tool in this evaluation.

### Context

- Ray Zimmerman was a Senior Research Associate at Cornell PSERC (Power Systems
  Engineering Research Center) from 1996 until mid-2024.
- He is the original author and sole architect of MATPOWER, MIPS, MP-Opt-Model,
  MOST, and MPTEST.
- He left Cornell in mid-2024 but continues contributing as an independent
  developer.
- The second contributor (eranschweitzer, 17 commits) contributed SynGrid
  (synthetic grid generation) as an extra, not core MATPOWER code.
- Wilson Gonzalez Vanegas (WilsonGV, 9 commits) is the most active recent
  contributor beyond Zimmerman, working on three-phase extensions.

## Risk Assessment

| Factor | Assessment |
|--------|-----------|
| Code knowledge concentration | Critical — one person holds all architectural knowledge |
| Succession planning | None visible — no co-maintainer, no formal handoff |
| Community depth | Shallow — 17 contributors total, most with 1-3 commits |
| Institutional backing | Weakened — left Cornell, no new institutional home |
| Mitigation | BSD-3 license enables forking; codebase is well-structured |

## Conclusion

MATPOWER has the highest contributor concentration risk of any tool evaluated.
The project's 28-year history is effectively the work product of a single
individual. While the BSD license and clean codebase enable community forking,
there is no evidence of succession planning or maintainer diversification.
