---
test_id: E-6
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

# E-6: CI/Test Coverage

## Summary

PowerSimulations.jl has a **comprehensive CI pipeline** with multi-platform testing, code coverage reporting via Codecov, format checking, cross-package integration tests, and performance benchmarking. Code coverage is reported at **100%** on the Codecov badge.

## CI Workflows

The project has **8 GitHub Actions workflows** in `.github/workflows/`:

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `main-tests.yml` | Push to main, hourly cron | Full test matrix (Julia stable + nightly, Linux/Windows/macOS) |
| `pr_testing.yml` | Pull requests | Test matrix (Julia stable, Linux/Windows/macOS) |
| `format-check.yml` | Push to main/release, PRs | JuliaFormatter code style enforcement |
| `cross-package-test.yml` | Push to main, PRs | Integration tests with downstream packages |
| `performance_comparison.yml` | -- | Performance benchmarking |
| `docs.yml` | -- | Documentation build |
| `doc-preview-cleanup.yml` | -- | Documentation PR preview cleanup |
| `TagBot.yml` | -- | Automated release tagging |

## Test Matrix Details

### Main Tests (`main-tests.yml`)
- **Julia versions:** stable (`1`) and `nightly`
- **Platforms:** ubuntu-latest, windows-latest, macOS-latest
- **Schedule:** Runs on every push to main AND hourly via cron
- **Coverage:** Uploads to Codecov with `julia-processcoverage` and `codecov-action`
- **Nightly tolerance:** `continue-on-error: true` for nightly Julia builds

### PR Tests (`pr_testing.yml`)
- **Julia versions:** stable (`1`) only
- **Platforms:** ubuntu-latest, windows-latest, macOS-latest
- **Coverage:** Uploads to Codecov

### Cross-Package Tests (`cross-package-test.yml`)
- Tests against downstream packages: **HydroPowerSimulations**, **StorageSystemsSimulations**, **PowerAnalytics**
- Ensures changes don't break the broader Sienna ecosystem
- `continue-on-error: true` (non-blocking but monitored)

### Format Check (`format-check.yml`)
- Runs JuliaFormatter on all code
- Uses `reviewdog/action-suggester` to post formatting suggestions on PRs
- Fails CI if code is not properly formatted

## Test Suite

The test suite contains **37 test files** covering:

- Device constructors (thermal, renewable, load, branch, HVDC, LCC, source, synchronous condenser)
- Network constructors
- Model types (decision, emulation)
- Simulation lifecycle (build, execute, results, export, partitions, sequence)
- Formulation combinations
- Cost models (market bid cost, import/export)
- Events and recorder
- Power flow in the loop
- Performance benchmarks (separate directory)
- Utility functions

## Code Coverage

- **Codecov badge:** 100% (as of 2026-03-06)
- **Coverage tool:** `julia-actions/julia-processcoverage` generating `lcov.info`
- **Reporting:** Codecov with `unittests` flag

## Observations

- The hourly cron schedule on `main-tests.yml` is unusually aggressive -- most projects use daily or weekly. This may be for catching flaky tests or upstream breakage.
- Cross-package integration testing is a strong signal of ecosystem maturity -- changes are validated against downstream consumers before merge.
- 100% coverage on the badge is notable; however, Julia coverage tools measure line coverage which may not reflect branch coverage or edge case coverage.
- Three-platform testing (Linux, Windows, macOS) ensures portability.
- No evidence of mutation testing, property-based testing, or formal verification.

## Sources

- CI workflows: <https://github.com/NREL-Sienna/PowerSimulations.jl/tree/main/.github/workflows>
- Codecov: <https://codecov.io/gh/NREL-Sienna/PowerSimulations.jl>
- Test directory: <https://github.com/NREL-Sienna/PowerSimulations.jl/tree/main/test>
