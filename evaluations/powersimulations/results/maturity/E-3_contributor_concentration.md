---
test_id: E-3
tool: powersimulations
dimension: maturity
network: N/A
protocol_version: "v4"
status: informational
workaround_class: null
wall_clock_seconds: null
peak_memory_mb: null
loc: null
solver: null
timestamp: "2026-03-07T05:00:00Z"
---

# E-3: Contributor Concentration

## Summary

PowerSimulations.jl has **high contributor concentration** over its lifetime, with one developer (Jose Daniel Lara / jd-lara) responsible for 70.7% of all commits. The top 3 contributors account for 82.5% of lifetime commits. However, recent (last 12 months) data shows meaningful diversification.

## All-Time Top Contributors

| Rank | Contributor | Commits | Share |
|------|------------|---------|-------|
| 1 | jd-lara (Jose Daniel Lara) | 7,537 | 70.7% |
| 2 | sourabhdalvi | 680 | 6.4% |
| 3 | claytonpbarrows | 577 | 5.4% |
| 4 | rodrigomha | 513 | 4.8% |
| 5 | daniel-thom | 401 | 3.8% |
| 6 | GabrielKS | 194 | 1.8% |
| 7 | Lilyhanig | 191 | 1.8% |
| 8 | m-bossart | 158 | 1.5% |
| 9 | SebastianManriqueM | 127 | 1.2% |
| 10 | kdheepak | 85 | 0.8% |

- **Total contributors:** 20
- **Total commits:** 10,667
- **Top 1 concentration:** 70.7%
- **Top 3 concentration:** 82.5%

## Bus Factor Analysis

**Lifetime bus factor: 1** -- Jose Daniel Lara is overwhelmingly the primary contributor with 7,537 of 10,667 commits (70.7%).

**Recent bus factor (last 12 months): ~2-3** -- In the last 12 months, Lara's share has dropped to 38.2%, with 5 other contributors each contributing >7% of commits (m-bossart, rodrigomha, GabrielKS, Luke Kiernan, SebastianManriqueM).

## Institutional Context

All significant contributors appear to be NREL-affiliated researchers, based on the NREL-Sienna GitHub organization membership. This means:

- **Single-institution risk:** If NREL defunds the Sienna project, development would likely halt.
- **Team growth:** The contributor base is growing within NREL, with newer contributors (GabrielKS, m-bossart, SebastianManriqueM) taking on larger shares.
- **Knowledge transfer:** The declining concentration of Lara in recent commits suggests active knowledge transfer within the team.

## Source

- GitHub API: `repos/NREL-Sienna/PowerSimulations.jl/contributors?per_page=20`
- Recent commit analysis: `repos/NREL-Sienna/PowerSimulations.jl/commits?since=2025-03-06`
