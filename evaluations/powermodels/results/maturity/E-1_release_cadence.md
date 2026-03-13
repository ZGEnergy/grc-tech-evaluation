---
test_id: E-1
tool: powermodels
dimension: maturity
network: N/A
status: pass
workaround_class: null
timestamp: 2026-03-11T00:00:00Z
protocol_version: "v9"
skill_version: v1
test_hash: "5748452f"
---

# E-1: release_cadence

## Finding

PowerModels.jl has made 5 releases in the last 24 months (March 2024–March 2026), all following semver convention, with the latest release (v0.21.5) on 2025-08-12. The project maintains a machine-readable changelog.

## Evidence

### Releases in last 24 months (since 2024-03-11):

| Tag | Date | Pre-release |
|-----|------|-------------|
| v0.21.5 | 2025-08-12 | No |
| v0.21.4 | 2025-05-20 | No |
| v0.21.3 | 2024-11-04 | No |
| v0.21.2 | 2024-07-05 | No |
| v0.21.1 | 2024-03-16 | No |

- **release_count_24mo:** 5
- **last_release_date:** 2025-08-12 (v0.21.5)
- **semver_used:** Yes — all tags follow `vMAJOR.MINOR.PATCH`; major version is 0 indicating API instability is possible but respected in practice via breaking-change annotations
- **changelog_quality:** High — `CHANGELOG.md` exists at repo root, is maintained per release with linked PR numbers, and breaking changes are explicitly labeled

GitHub releases page: <https://github.com/lanl-ansi/PowerModels.jl/releases>

The cadence averages roughly one release every 5 months. Note that v0.21.4 was a significant release bundling 14 PRs (April–May 2025 period); v0.21.5 was minor. No releases have occurred after August 2025.

## Implications

Five releases in 24 months with intact semver and a maintained changelog demonstrates an active, well-managed release process. The 7-month gap from the last release (Aug 2025) to the evaluation date (Mar 2026) is modest and not alarming given the minor nature of recent changes. This is a positive maturity signal.
