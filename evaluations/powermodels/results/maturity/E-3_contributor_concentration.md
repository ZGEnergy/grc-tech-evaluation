---
test_id: E-3
tool: powermodels
dimension: maturity
network: N/A
protocol_version: "v4"
status: fail
workaround_class: null
timestamp: 2026-03-07T00:00:00Z
---

# E-3: Contributor Concentration

## Result: FAIL

## Finding

PowerModels.jl has extreme contributor concentration. The original author (Carleton Coffrin, LANL) accounts for 82.4% of all commits. The top 3 contributors account for 90.2% of all commits. The bus factor is effectively 1, though a maintainer transition appears to be underway from ccoffrin to odow (Oscar Dowson).

## Evidence

**Total contributors:** 27
**Total commits (GitHub API):** 1,009

**Top contributors by commit volume (lifetime):**

| Rank | Contributor   | Commits | Percentage |
|------|---------------|---------|------------|
| 1    | ccoffrin      | 831     | 82.4%      |
| 2    | pseudocubic   | 45      | 4.5%       |
| 3    | jd-lara       | 34      | 3.4%       |
| 4    | odow          | 22      | 2.2%       |
| 5    | rb004f        | 15      | 1.5%       |

**Key metrics:**
- Top contributor percentage: 82.4%
- Top 3 contributor percentage: 90.2%
- Bus factor: 1

**Notable transition:** In the last 12 months, ccoffrin has 0 commits while odow (Oscar Dowson, JuMP core team) has 17 of 20 human commits. This suggests an informal maintainer handoff is underway. However, odow's lifetime contribution is still only 2.2%, and the transition is not formalized.

**Organizational diversity:** The project is LANL-led. odow is affiliated with the broader JuMP ecosystem (not LANL). pseudocubic and jd-lara appear to be NREL-affiliated (PowerSystems.jl ecosystem). There is minimal industry contributor representation.

Source: <https://github.com/lanl-ansi/PowerModels.jl/graphs/contributors>

## Implications

The extreme concentration on a single contributor is a significant maturity risk. While the apparent transition to odow as active maintainer provides some continuity, it replaces single-person risk with a different single-person risk. The project would benefit from formalizing governance and broadening the maintainer base. For production adoption, this concentration represents a material continuity risk.
