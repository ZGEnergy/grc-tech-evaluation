---
test_id: E-6
tool: powersimulations
dimension: maturity
network: N/A
protocol_version: "v11"
skill_version: "v2"
test_hash: "b8b60049"
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

# E-6: CI/CD & Test Coverage

## Result: INFORMATIONAL

## Finding

PowerSimulations.jl has a comprehensive CI/CD pipeline with automated testing on every push and PR across three OS platforms, coverage reporting via Codecov (79% on main as of 2026-03-24), and additional workflows for formatting, documentation, cross-package compatibility, and performance regression testing. The test suite contains 41 entries in the `test/` directory (including 33+ dedicated test files, a `performance/` subdirectory, test data, and utilities). CI is actively passing on the main branch.

## Evidence

### CI Workflows

Eight workflow files in `.github/workflows/`:

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `main-tests.yml` | Push to main + hourly cron | Full test matrix: Julia release + nightly on Ubuntu, Windows, macOS |
| `pr_testing.yml` | Pull request (open/sync/reopen) | Same matrix but Julia release only (3 OS) |
| `format-check.yml` | Pull request | Code formatting validation |
| `docs.yml` | Push/PR | Documentation build |
| `cross-package-test.yml` | On demand | Integration tests across Sienna ecosystem |
| `performance_comparison.yml` | On demand | Performance regression benchmarks |
| `TagBot.yml` | Issue comment / schedule | Automated release tagging |
| `doc-preview-cleanup.yml` | PR close | Cleanup doc preview artifacts |

### Main CI Configuration

The `main-tests.yml` workflow runs:
- **Matrix:** Julia `1` (latest stable) and `nightly` on `ubuntu-latest`, `windows-latest`, `macOS-latest` (6 jobs)
- **Steps:** checkout, setup-julia, julia-buildpkg, julia-runtest, julia-processcoverage, codecov upload
- **Nightly failures are non-blocking** (`continue-on-error: true` for nightly only)
- **Cron schedule:** runs hourly (`0 * * * *`) to catch upstream breakage early

### Recent CI Status

Last 5 Main - CI runs on `main` branch (queried 2026-03-24 via `gh api`):

| Date | Branch | Conclusion |
|------|--------|------------|
| 2026-03-24 | main | success |
| 2026-03-24 | main | success |
| 2026-03-21 | main | success |
| 2026-03-21 | main | success |
| 2026-03-21 | main | success |

CI is actively passing. One failure on 2026-03-19 was quickly followed by fixes that restored green status.

### Test Suite Structure

The `test/` directory contains 41 entries including 33+ test files:

- **Device constructors (8):** `test_device_thermal_generation_constructors.jl`, `test_device_renewable_generation_constructors.jl`, `test_device_branch_constructors.jl`, `test_device_load_constructors.jl`, `test_device_hvdc.jl`, `test_device_lcc.jl`, `test_device_source_constructors.jl`, `test_device_synchronous_condenser_constructors.jl`
- **Network formulations (2):** `test_network_constructors.jl`, `test_network_constructors_with_dlr.jl`
- **Model types (2):** `test_model_decision.jl`, `test_model_emulation.jl`
- **Simulation (7):** `test_simulation_build.jl`, `test_simulation_execute.jl`, `test_simulation_models.jl`, `test_simulation_partitions.jl`, `test_simulation_results.jl`, `test_simulation_results_export.jl`, `test_simulation_sequence.jl`, `test_simulation_store.jl`
- **Services:** `test_services_constructor.jl`
- **Cost modeling (3):** `test_import_export_cost.jl`, `test_market_bid_cost.jl`, `test_mbc_sanity_check.jl`
- **Infrastructure (4):** `test_basic_model_structs.jl`, `test_formulation_combinations.jl`, `test_problem_template.jl`, `test_jump_utils.jl`, `test_initialization_problem.jl`
- **Integration:** `test_power_flow_in_the_loop.jl`, `run_partitioned_simulation.jl`
- **Other:** `test_print.jl`, `test_recorder_events.jl`, `test_events.jl`, `test_utils.jl`
- **Support:** `test_utils/` directory, `test_data/` directory, `performance/` subdirectory

### Code Coverage

- **Codecov badge on main:** 79% (verified via badge SVG text element `<text x="93" y="14">79%</text>`)
- **Source:** `https://codecov.io/gh/NREL-Sienna/PowerSimulations.jl/branch/main/graph/badge.svg` (fetched 2026-03-24)
- Coverage is measured via `julia-processcoverage` (generates lcov.info) and uploaded to Codecov on every CI run
- Coverage reports are generated on both main pushes and PR runs

### Data Source

- `gh api repos/NREL-Sienna/PowerSimulations.jl/contents/.github/workflows` (accessed 2026-03-24)
- `gh api repos/NREL-Sienna/PowerSimulations.jl/actions/workflows/55944568/runs` (accessed 2026-03-24)
- `gh api repos/NREL-Sienna/PowerSimulations.jl/contents/test` (accessed 2026-03-24)
- Codecov badge SVG (fetched 2026-03-24, verified via WebFetch tool)

## Implications

1. **Multi-platform testing:** All three major OS platforms are tested on every commit, reducing platform-specific regressions.
2. **Coverage tracking:** 79% coverage is solid for a package of this complexity. Coverage is measured automatically and reported to Codecov on every run.
3. **Proactive breakage detection:** Hourly cron runs on main catch upstream Julia or dependency breakage before developers encounter it.
4. **Ecosystem awareness:** The cross-package test workflow tests compatibility across the Sienna ecosystem (PowerSystems, InfrastructureSystems, etc.), which is critical given the tightly coupled package family.
5. **Performance monitoring:** Dedicated performance comparison workflow prevents silent performance regressions.
6. **Active CI health:** The main branch shows consistent green CI with rapid recovery from the single failure observed in the 10-run history.

The main gap is that nightly Julia failures are allowed to pass silently (`continue-on-error`), which could mask forward-compatibility issues. However, this is standard practice in the Julia ecosystem.
