---
test_id: E-1
tool: powersimulations
dimension: maturity
network: N/A
protocol_version: "v10"
skill_version: "v1"
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
timestamp: 2026-03-14T00:00:00Z
---

# E-1: Release Cadence

## Result: INFORMATIONAL

## Finding

PowerSimulations.jl maintains an active release cadence with 21 releases in the last 24 months, averaging roughly one release per month. The most recent release (v0.33.1) was published on 2026-02-24. Companion packages show comparable or higher activity. All releases follow strict semver.

## Evidence

### PowerSimulations.jl — 21 releases since 2024-03-14

| Version | Date | Gap (days) |
|---------|------|------------|
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
| v0.27.8 | 2024-03-27 | 9 |
| v0.27.7 | 2024-03-18 | 0 |
| v0.27.6 | 2024-03-18 | — |

Last release: v0.33.1 on 2026-02-24 (18 days ago).

Notable gap: v0.28.3 to v0.29.0 = 141 days (Jul–Dec 2024), followed by a burst of 7 releases in Dec 2024 – Feb 2025 coinciding with the v0.29–v0.30 development cycle. A second gap of 155 days (Jun–Nov 2025) preceded the v0.31–v0.32 burst (6 releases in 4 weeks).

Semver compliance: All 21 releases use proper semver (major.minor.patch). The project is still pre-1.0 (v0.x) which by semver convention means the API is not yet considered stable.

### Companion Packages (last 24 months)

| Package | Releases | Latest | Latest Date |
|---------|----------|--------|-------------|
| PowerSystems.jl | 27 (incl. v3.x → v5.x) | v5.5.0 | 2026-02-12 |
| PowerFlows.jl | 12 | v0.16.0 | 2026-02-13 |

PowerSystems.jl underwent a major version bump (v4 → v5) in Nov 2025, indicating active evolution. PowerFlows.jl released 8 versions in the Nov 2025 – Feb 2026 window alone, coinciding with the PowerSimulations v0.32–v0.33 cycle.

### Data Source

- `gh api repos/NREL-Sienna/PowerSimulations.jl/releases --paginate` (accessed 2026-03-14)
- `gh api repos/NREL-Sienna/PowerSystems.jl/releases --paginate` (accessed 2026-03-14)
- `gh api repos/NREL-Sienna/PowerFlows.jl/releases --paginate` (accessed 2026-03-14)

## Implications

The release cadence is strong — 21 releases in 24 months with the most recent only 18 days old. The bursty pattern (long quiet periods followed by rapid-fire releases) is typical of research-lab development where features accumulate on main and are released in batches. The ecosystem packages are tightly coordinated, often releasing within days of each other. Pre-1.0 status means API breaking changes remain possible, which is a minor risk for adopters but standard for actively evolving Julia packages.
