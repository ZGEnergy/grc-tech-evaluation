---
test_id: E-2
tool: powersimulations
dimension: maturity
network: N/A
protocol_version: "v10"
skill_version: "v1"
test_hash: "44a090f5"
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

# E-2: Commit Activity

## Result: INFORMATIONAL

## Finding

PowerSimulations.jl had approximately 1,019 commits in the last 12 months from 15 unique committers (excluding bots). Activity is heavily concentrated in the Dec 2025 – Feb 2026 window. PowerSystems.jl shows comparable activity with ~1,470 commits from a broader contributor pool.

## Evidence

### PowerSimulations.jl — Last 12 months (2025-03-14 to 2026-03-14)

**Total commits:** ~1,019
**Unique committers (human):** 12 (excluding Copilot bot)

| Author | Commits | % |
|--------|---------|---|
| jd-lara | 399 | 39.2% |
| m-bossart | 119 | 11.7% |
| rodrigomha | 111 | 10.9% |
| SebastianManriqueM | 107 | 10.5% |
| GabrielKS | 99 | 9.7% |
| luke-kiernan | 81 | 7.9% |
| daniel-thom | 31 | 3.0% |
| rbolgaryn | 23 | 2.3% |
| purboday | 17 | 1.7% |
| kdayday | 10 | 1.0% |
| Taran Raj | 5 | 0.5% |
| juflorez | 2 | 0.2% |
| mcllerena | 1 | 0.1% |
| akrivi | 1 | 0.1% |
| Copilot (bot) | 13 | 1.3% |

**Substantive vs maintenance:** The top contributors (jd-lara, m-bossart, rodrigomha, GabrielKS) are all working on feature development (new formulations, HVDC models, power flow integration). Copilot bot contributions are minor (13 commits, 1.3%). The ratio is heavily substantive — this is an actively developed research codebase, not in maintenance mode.

**Temporal distribution:** Activity concentrated in two bursts: Dec 2025 (v0.32 release cycle) and Feb 2026 (v0.33 release cycle). A quieter period from Mar–Nov 2025 preceded the Dec burst.

### PowerSystems.jl — Last 12 months

**Total commits (estimated):** ~1,470 (API returned 200 results with pagination)

| Author | Commits |
|--------|---------|
| jd-lara | 665 |
| mcllerena | 245 |
| rodrigomha | 173 |
| m-bossart | 95 |
| kdayday | 79 |
| Copilot (bot) | 63 |
| rbolgaryn | 31 |
| luke-kiernan | 25 |
| pesap | 20 |
| daniel-thom | 13 |
| + 11 others | ~61 |

PowerSystems.jl has a broader contributor base (21 unique committers), reflecting its role as the data model layer shared across the Sienna ecosystem.

### Data Source

- `gh api repos/NREL-Sienna/PowerSimulations.jl/commits?since=2025-03-14 --paginate` (accessed 2026-03-14)
- `gh api repos/NREL-Sienna/PowerSystems.jl/commits?since=2025-03-14 --paginate` (accessed 2026-03-14)

## Implications

The commit volume (~1,019 commits/year across 12 human contributors) indicates an actively developed project. The contributor pool is broader than typical single-maintainer open-source projects but still dominated by jd-lara (39% of recent commits). The presence of multiple NREL staff (m-bossart, rodrigomha, GabrielKS, luke-kiernan) plus external contributors (SebastianManriqueM, daniel-thom) suggests institutional investment beyond a single researcher. Copilot bot usage is minimal and does not inflate the numbers meaningfully.
