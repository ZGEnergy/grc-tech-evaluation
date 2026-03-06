---
test_id: E-6
tool: powermodels
dimension: maturity
status: pass
timestamp: 2026-03-05
---

# E-6: CI/Test Coverage

## Finding

PowerModels.jl has comprehensive CI with cross-platform testing (Linux, macOS, Windows) on Julia 1.10 and latest, with 94% code coverage reported via Codecov. CI runs on push, PR, and weekly schedule.

## Evidence

**CI Configuration** (`.github/workflows/ci.yml`):
- Triggers: push to master/release-*, PRs, weekly cron (Wednesday)
- Matrix: Julia 1.10 + latest, on ubuntu-latest + macOS-latest + windows-latest (all x64)
- Steps: checkout, setup-julia, cache, buildpkg, runtest, processcoverage, codecov upload
- Total: 6 CI configurations per run

**Coverage**: 94% (from Codecov badge at <https://codecov.io/gh/lanl-ansi/PowerModels.j>l)

**Additional CI workflows**:
- `CompatHelper.yml` -- automated dependency compatibility checking
- `TagBot.yml` -- automated release tagging
- `documentation.yml` + `documentation-deploy.yml` -- docs build and deployment

**Test suite**: Julia standard `test/runtests.jl` executed via `julia-actions/julia-runtest@latest`.

Source: <https://github.com/lanl-ansi/PowerModels.jl/blob/master/.github/workflows/ci.yml,> Codecov badge

## Implications

94% code coverage is excellent for a power systems optimization package. Cross-platform CI with multiple Julia versions ensures compatibility. The weekly scheduled runs catch upstream breakage proactively. This is a strong pass for CI/test maturity.
