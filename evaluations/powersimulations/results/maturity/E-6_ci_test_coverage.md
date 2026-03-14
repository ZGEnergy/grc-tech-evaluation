---
test_id: E-6
tool: powersimulations
dimension: maturity
network: N/A
protocol_version: "v10"
skill_version: "v1"
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
timestamp: 2026-03-14T00:00:00Z
---

# E-6: CI/CD & Test Coverage

## Result: INFORMATIONAL

## Finding

PowerSimulations.jl has a comprehensive CI/CD pipeline with automated testing on every push and PR across three OS platforms, coverage reporting via Codecov (78% on main), and additional workflows for formatting, documentation, cross-package compatibility, and performance regression testing. The test suite contains 29+ dedicated test files covering device constructors, network formulations, model types, and simulation workflows.

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

Most recent Main - CI runs on `main` branch (queried 2026-03-14):

| Date | Branch | Conclusion |
|------|--------|------------|
| 2026-03-03 | main | success |
| 2026-03-02 | main | success |

CI is passing on the current main branch.

### Test Suite Structure

The `test/` directory contains 29+ test files:

- **Device constructors:** `test_device_thermal_generation_constructors.jl`, `test_device_renewable_generation_constructors.jl`, `test_device_branch_constructors.jl`, `test_device_load_constructors.jl`, `test_device_hvdc.jl`, `test_device_lcc.jl`, `test_device_source_constructors.jl`, `test_device_synchronous_condenser_constructors.jl`
- **Network formulations:** `test_network_constructors.jl`
- **Model types:** `test_model_decision.jl`, `test_model_emulation.jl`
- **Services:** `test_services_constructor.jl`
- **Cost modeling:** `test_import_export_cost.jl`, `test_market_bid_cost.jl`, `test_mbc_sanity_check.jl`
- **Infrastructure:** `test_basic_model_structs.jl`, `test_formulation_combinations.jl`, `test_problem_template.jl`, `test_jump_utils.jl`, `test_initialization_problem.jl`
- **Integration:** `test_power_flow_in_the_loop.jl`, `run_partitioned_simulation.jl`
- **Other:** `test_print.jl`, `test_recorder_events.jl`, `test_events.jl`
- **Performance:** `performance/` subdirectory

### Code Coverage

- **Codecov badge on main:** 78%
- **Source:** `https://codecov.io/gh/NREL-Sienna/PowerSimulations.jl/branch/main/graph/badge.svg` (accessed 2026-03-14)
- Coverage is measured via `julia-processcoverage` (generates lcov.info) and uploaded to Codecov on every CI run
- Coverage reports are generated on both main pushes and PR runs

### Data Source

- `gh api repos/NREL-Sienna/PowerSimulations.jl/contents/.github/workflows` (accessed 2026-03-14)
- `gh api repos/NREL-Sienna/PowerSimulations.jl/actions/runs` (accessed 2026-03-14)
- Codecov badge SVG (accessed 2026-03-14)

## Implications

The CI/CD setup is thorough for an open-source research package:

1. **Multi-platform testing:** All three major OS platforms are tested on every commit, reducing platform-specific regressions.
2. **Coverage tracking:** 78% coverage is solid for a package of this complexity. Coverage is measured automatically, not manually reported.
3. **Proactive breakage detection:** Hourly cron runs on main catch upstream Julia or dependency breakage before developers encounter it.
4. **Ecosystem awareness:** The cross-package test workflow tests compatibility across the Sienna ecosystem (PowerSystems, InfrastructureSystems, etc.), which is critical given the tightly coupled package family.
5. **Performance monitoring:** Dedicated performance comparison workflow prevents silent performance regressions.

The main gap is that nightly Julia failures are allowed to pass silently (`continue-on-error`), which could mask forward-compatibility issues. However, this is standard practice in the Julia ecosystem.
