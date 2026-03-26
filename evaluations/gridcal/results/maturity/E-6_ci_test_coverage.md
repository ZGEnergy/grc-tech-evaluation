---
test_id: E-6
tool: gridcal
dimension: maturity
network: N/A
protocol_version: "v11"
skill_version: v2
test_hash: "0a914eea"
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: estimated
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: null
solver: null
timestamp: "2026-03-24T00:00:00Z"
---

# E-6: CI Configuration and Test Coverage

## Result: INFORMATIONAL

## Finding

CI is minimal and partially broken. The only CI workflow (Pylint) is manually disabled. GitHub Actions runs only CodeQL (security scanning) and Dependabot on a scheduled basis. There is no automated test execution in CI despite 102 test files existing in the repository. No coverage measurement or reporting is configured.

## Evidence

**GitHub Actions workflows (accessed 2026-03-24):**

| Workflow | Status | Purpose |
|----------|--------|---------|
| Pylint | **disabled_manually** | Static analysis |
| Dependabot Updates | active | Dependency updates |
| CodeQL | active | Security scanning |
| pages-build-deployment | active | Documentation hosting |

The Pylint workflow (`.github/workflows/pylint.yml`) is disabled. When it was active, it ran on Python 3.8, 3.9, 3.10 (the project requires Python 3.12) and only installed `pylint` without installing `veragridengine` or its dependencies -- meaning it could not have successfully analyzed the codebase.

**Recent CI runs (accessed 2026-03-24):**

| Date | Workflow | Status |
|------|----------|--------|
| 2026-03-23 | Scheduled (CodeQL) | success |
| 2026-03-16 | Scheduled (CodeQL) | success |
| 2026-03-10 | Scheduled (CodeQL) | success |
| 2026-03-09 | Push on master (CodeQL) | success |
| 2026-03-02 | Scheduled (CodeQL) | success |

Only CodeQL security scans are running. No pytest, no linting, no type checking.

**Test suite (repository inspection):**
- Location: `src/tests/` in the repository
- Test file count: **102** Python files matching `test_*.py`
- Total files under `src/tests/`: 559 (including data files, grids, `__init__.py` files)
- Test runner configuration: `pytest.ini` exists (`testpaths = src/tests`, `pythonpath = src src/tests`)
- Tox configuration: `tox.ini` exists but targets Python 3.6/3.7 (severely outdated)

**Test directory structure by domain:**
Base, Contingencies, EMT, FileFormats (CGMES subdirectory), GSLV, Linear, LinearOPF, NTC, NonLinearOPF, PowerFlow, RMS, ShortCircuit, SmallSignal, StateEstimation, Stochastic, ThreePhasePowerFlow

**Coverage measurement:**
- No `.coveragerc` file
- No `setup.cfg` with coverage configuration
- No coverage section in `pyproject.toml`
- No coverage badges in README
- No coverage reporting in any CI workflow
- **Coverage percentage: unknown/unmeasured**

**Branch protection:**
- No required status checks visible
- No branch protection rules on master/main
- All PRs in the E-3 sample were merged without CI gates

**Consumed observation -- arch-quality (B-6):** Internal docstring coverage varies significantly: data model layer (assets.py, multi_circuit.py) has 74-82% docstring coverage, but the simulation/worker layer has poor coverage (12-14%). The monolithic OPF formulation (linear_opf_ts.py, 3146 LOC) has minimal inline documentation.

Sources:
- GitHub API: `repos/SanPen/GridCal/actions/workflows` and `runs` (accessed 2026-03-24)
- GitHub API: `repos/SanPen/GridCal/contents/pytest.ini`, `tox.ini`, `.github/workflows/pylint.yml` (accessed 2026-03-24)
- GitHub API: `repos/SanPen/GridCal/git/trees/master?recursive=1` (test file count, accessed 2026-03-24)

## Implications

The absence of automated testing in CI is a significant maturity gap. While 102 test files exist (covering power flow, OPF, contingencies, file formats, and more), they are not executed in any automated pipeline. The disabled Pylint workflow and outdated tox config (Python 3.6/3.7) suggest CI maintenance is not prioritized. The combination of no CI testing, no code review (E-3), and no branch protection means there is no automated quality assurance visible to external stakeholders. Regressions can be introduced through any push or merge without detection. For an operational deployment, this would require the adopter to establish their own test and validation pipeline.
