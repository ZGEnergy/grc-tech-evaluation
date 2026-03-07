---
test_id: E-6
tool: pypsa
dimension: maturity
slug: ci_test_coverage
network: N/A
protocol_version: v4
status: informational
workaround_class: null
timestamp: 2026-03-06T18:00:00Z
---

# E-6: CI/CD and Test Coverage

## Summary

| Metric | Value |
|--------|-------|
| CI platform | GitHub Actions |
| CI workflows | 4 (Tests, Test models, CodeQL, Release) |
| Test framework | pytest |
| Test files | 78 Python test files |
| Code coverage | ~84% (Codecov) |
| Coverage tool | coverage.py + Codecov |
| CI frequency | Every push to master, every PR, daily scheduled (cron `0 5 * * *`) |
| Latest CI status (2026-03-06) | All passing |

## CI Workflow Details

### 1. Tests (`test.yml`)

The primary test workflow runs on every push to `master`, every PR, and daily via cron.

**Matrix:**
- Python versions: All supported classifiers (dynamically determined from package metadata, includes 3.12, 3.13, 3.14)
- Operating systems: ubuntu-latest, macos-latest, windows-latest
- API variants: `default` and `new_api` (new components API)

**Steps:**
1. Build and verify Python package (SDist + wheel)
2. Install package and dependencies via uv
3. Run pytest with `--cov=pypsa` for coverage measurement
4. Upload coverage to Codecov
5. Generate matplotlib comparison images for plot tests

**Concurrency:** Cancel-in-progress enabled per workflow/ref.

**Total matrix combinations:** ~13 (3 OS x 3 Python versions x 2 API variants, minus exclusions for macOS/Windows new_api).

### 2. Test Models (`test-models.yml`)

Integration tests against the full PyPSA-Eur model. Runs the same triggers as the main test workflow.

- Checks out PyPSA-Eur master
- Runs Snakemake-based model pipeline with the PR's PyPSA version
- Validates that upstream model code remains compatible

### 3. CodeQL (`codeql.yml`)

GitHub's code scanning for security vulnerabilities. Runs on push to master and PRs.

### 4. Release (`release.yml`)

Automated release pipeline for publishing to PyPI.

## Test Suite Structure

78 test files covering:

| Category | Test Files | Coverage Area |
|----------|-----------|---------------|
| Power flow | `test_pf_*.py`, `test_lpf_*.py` | AC PF, DC PF, distributed slack, validation against PyPOWER and pandapower |
| Optimization | `test_lopf_*.py` | DCOPF, unit commitment, losses, MGA, multi-period, rolling horizon, storage, quadratic costs |
| SCOPF | `test_sclopf_scigrid.py` | Security-constrained OPF |
| Components | `test_components*.py`, `test_buses.py`, `test_carriers.py` | Component store, custom types, array interface |
| I/O | `test_io.py`, `test_io_cloudpathlib.py` | NetCDF, CSV, HDF5, cloud storage |
| Network | `test_network*.py`, `test_graph.py` | Network operations, graph algorithms, cycles |
| Statistics | `test_statistics*.py` | Statistics module and plotting |
| Plotting | `test_plot_*.py` | Map plots (static + interactive), matplotlib image comparison |
| Stochastic | `test_stochastic*.py` | Stochastic optimization |
| Bugs | `test_bugs.py` | Regression tests for known issues |
| Other | `test_common.py`, `test_deprecations.py`, `test_version.py` | Utilities, API deprecation warnings |

## Coverage Configuration

From `pyproject.toml`:

```toml
[tool.coverage.run]
branch = true
source = ["pypsa"]
omit = ["test/*"]

[tool.coverage.report]
exclude_also = ["if TYPE_CHECKING:"]
```

From `codecov.yml`:

```yaml
coverage:
  status:
    project:
      default:
        threshold: 0.1%

codecov:
  notify:
    after_n_builds: 13    # Wait for all matrix builds
```

Coverage threshold is set to 0.1% regression tolerance. The `after_n_builds: 13` setting ensures Codecov waits for all matrix combinations before reporting.

## Assessment

PyPSA has a mature, well-structured CI/CD pipeline. Key strengths:

1. **Broad platform coverage**: Tests run on Linux, macOS, and Windows across multiple Python versions.
2. **Daily scheduled runs**: Catches upstream dependency breakage even without code changes.
3. **Integration testing**: The `test-models` workflow validates compatibility with the flagship PyPSA-Eur model.
4. **84% code coverage**: Solid coverage with branch analysis enabled.
5. **Security scanning**: CodeQL analysis on every PR.
6. **Regression testing**: Dedicated `test_bugs.py` for known issue regression tests.

The only gap is the absence of a formal coverage gate (the 0.1% threshold prevents regression but does not enforce a minimum coverage floor).
