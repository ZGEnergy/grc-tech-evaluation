---
test_id: E-1
tool: powermodels
dimension: maturity
network: N/A
protocol_version: v11
skill_version: v2
test_hash: 5748452f
status: pass
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

# E-1: Release Cadence

## Result: PASS

## Finding

PowerModels.jl has made 4 releases in the last 24 months (2024-03-24 to 2026-03-24), all following semver convention. The latest release is v0.21.5 (2025-08-12). The project maintains a CHANGELOG.md with linked PR numbers and breaking-change annotations.

## Evidence

### Releases in 24-month window (2024-03-24 to 2026-03-24)

| Tag | Date | Semver-compliant |
|-----|------|------------------|
| v0.21.2 | 2024-07-05 | Yes |
| v0.21.3 | 2024-11-04 | Yes |
| v0.21.4 | 2025-05-20 | Yes |
| v0.21.5 | 2025-08-12 | Yes |

Note: v0.21.1 (2024-03-16) falls outside the 24-month window by 8 days.

- **release_count_24mo:** 4
- **last_release_date:** 2025-08-12 (v0.21.5)
- **months_since_last_release:** ~7 months (as of 2026-03-24)
- **semver_used:** Yes -- all tags follow `vMAJOR.MINOR.PATCH`; major version 0 indicates pre-1.0 but API changes are managed via deprecation warnings and explicit breaking-change labels in CHANGELOG
- **changelog_quality:** High -- `CHANGELOG.md` maintained per release with linked PR numbers; breaking changes explicitly labeled
- **average_release_cadence:** ~6 months between releases

GitHub releases page: <https://github.com/lanl-ansi/PowerModels.jl/releases> (accessed 2026-03-24)

Since the last release (v0.21.5, Aug 2025), only 5 commits have landed on master -- 3 Dependabot bumps, 1 JSON@1 compatibility update, and 1 release prep. This suggests the project is in a stable maintenance phase rather than stalled.

### Julia General Registry

PowerModels.jl is registered in the Julia General Registry. All releases are discoverable via `Pkg.add("PowerModels")` and version-pinnable via standard Julia package management.

## Consumed Observations

Documentation gaps observed during expressiveness and extensibility testing (doc-gap observations for A-9 and B-6) indicate the API is functional but under-documented in areas like LODF computation and formulation-specific constraint methods. This does not affect release cadence assessment but contextualizes the documentation maturity alongside the release process.

## Implications

Four releases in 24 months with intact semver and a maintained changelog demonstrates a functioning release process. The cadence (~6 months between releases) is slower than some peer tools but consistent. The 7-month gap since the last release is not alarming given the stable nature of the codebase and the small number of unreleased commits. This is a positive maturity signal.
