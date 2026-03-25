---
test_id: E-1
tool: powersimulations
dimension: maturity
network: N/A
protocol_version: "v11"
skill_version: "v2"
test_hash: "5748452f"
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
timestamp: 2026-03-24T00:00:00Z
---

# E-1: Release Cadence

## Result: INFORMATIONAL

## Finding

PowerSimulations.jl maintains an active release cadence with 23 releases in the last 24 months, averaging roughly one release per month. The most recent release (v0.33.5) was published on 2026-03-21, three days before this audit. Companion packages show comparable or higher activity. All releases follow strict semver.

## Evidence

### PowerSimulations.jl — 23 releases since 2024-03-24

| Version | Date | Gap (days) |
|---------|------|------------|
| v0.33.5 | 2026-03-21 | 1 |
| v0.33.4 | 2026-03-20 | 1 |
| v0.33.3 | 2026-03-19 | 0 |
| v0.33.2 | 2026-03-19 | 23 |
| v0.33.1 | 2026-02-24 | 6 |
| v0.33.0 | 2026-02-18 | 62 |
| v0.32.4 | 2025-12-18 | 5 |
| v0.32.3 | 2025-12-13 | 3 |
| v0.32.2 | 2025-12-10 | 1 |
| v0.32.1 | 2025-12-09 | 1 |
| v0.32.0 | 2025-12-08 | 27 |
| v0.31.0 | 2025-11-11 | 155 |
| v0.30.2 | 2025-06-09 | 102 |
| v0.30.1 | 2025-02-27 | 21 |
| v0.30.0 | 2025-02-06 | 24 |
| v0.29.2 | 2025-01-13 | 18 |
| v0.29.1 | 2024-12-26 | 14 |
| v0.29.0 | 2024-12-12 | 141 |
| v0.28.3 | 2024-07-24 | 10 |
| v0.28.2 | 2024-07-14 | 5 |
| v0.28.1 | 2024-07-09 | 11 |
| v0.28.0 | 2024-06-28 | 93 |
| v0.27.8 | 2024-03-27 | — |

Last release: v0.33.5 on 2026-03-21 (3 days ago).

Notable gaps: v0.28.3 to v0.29.0 = 141 days (Jul-Dec 2024), followed by a burst of 7 releases in Dec 2024 - Feb 2025 coinciding with the v0.29-v0.30 development cycle. A second gap of 155 days (Jun-Nov 2025) preceded the v0.31-v0.32 burst (6 releases in 4 weeks). Most recently, 4 releases shipped in 3 days (Mar 19-21, 2026) during the v0.33.x patch cycle.

Semver compliance: All 23 releases use proper semver (major.minor.patch). The project is still pre-1.0 (v0.x) which by semver convention means the API is not yet considered stable.

### Companion Packages (last 24 months)

| Package | Releases | Latest | Latest Date |
|---------|----------|--------|-------------|
| PowerSystems.jl | 28 (incl. v4.x to v5.x) | v5.6.1 | 2026-03-19 |
| PowerFlows.jl | 13 | v0.16.1 | 2026-03-16 |

PowerSystems.jl underwent a major version bump (v4 to v5) in Nov 2025 and has continued through v5.6.1, indicating active evolution. PowerFlows.jl released 9 versions in the Nov 2025 - Mar 2026 window, coinciding with the PowerSimulations v0.32-v0.33 cycle. All three packages released within the same week (Mar 16-21, 2026).

### Data Source

- `gh api repos/NREL-Sienna/PowerSimulations.jl/releases --paginate` (accessed 2026-03-24)
- `gh api repos/NREL-Sienna/PowerSystems.jl/releases --paginate` (accessed 2026-03-24)
- `gh api repos/NREL-Sienna/PowerFlows.jl/releases --paginate` (accessed 2026-03-24)

## Implications

The release cadence is strong — 23 releases in 24 months with the most recent only 3 days old. The bursty pattern (long quiet periods followed by rapid-fire releases) is typical of research-lab development where features accumulate on main and are released in batches. The ecosystem packages are tightly coordinated, often releasing within days of each other. Pre-1.0 status means API breaking changes remain possible, which is a minor risk for adopters but standard for actively evolving Julia packages.
