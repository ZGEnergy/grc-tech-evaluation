---
test_id: E-6
tool: gridcal
dimension: maturity
network: N/A
status: informational
workaround_class: null
protocol_version: "v10"
skill_version: v1
test_hash: "0a914eea"
timestamp: "2026-03-13T23:00:00Z"
---

# E-6: CI Configuration and Test Coverage

## Finding

The CI configuration is minimal — a single pylint workflow running on push. There is no automated test execution, no coverage reporting, and no branch protection. The repository contains 125 test files under `src/tests/` but these are not run in CI.

## Evidence

**CI configuration:**
- Single workflow file: `.github/workflows/pylint.yml`
- Trigger: `on: [push]` (every push to any branch)
- Matrix: Python 3.8, 3.9, 3.10 (outdated — project requires 3.12)
- Actions: `checkout@v3`, `setup-python@v3` (both outdated; current versions are v4)
- Steps: `pip install pylint` only — does **not** install `veragridengine` or its dependencies
- The pylint workflow likely fails on most runs because the analyzed code imports `VeraGridEngine` which is not installed

**Test suite:**
- Location: `src/tests/` in the repository
- Test file count: 125 Python test files
- Test directories by domain: Base, Contingencies, EMT, FileFormats, GSLV, Linear, LinearOPF, NTC, NonLinearOPF, PowerFlow, QA_actions_list.txt, RMS, ShortCircuit, SmallSignal, StateEstimation, Stochastic, ThreePhasePowerFlow
- Test runner: `tox.ini` references `pytest src/tests` but tox config targets Python 3.6/3.7 (very outdated)
- No `pytest` invocation in any CI workflow

**Coverage reporting:**
- No coverage configuration found (`setup.cfg` is absent, `pyproject.toml` has no coverage section)
- No coverage badges in README
- No evidence of coverage measurement in any workflow or config file

**Branch protection:**
- No evidence of required status checks or branch protection rules
- All PRs in the sample were merged without review or CI gates

## Implications

The absence of automated testing in CI is a significant maturity gap. While 125 test files exist (suggesting the developers do run tests locally), the lack of CI execution means regressions can be introduced through any push or merge. The outdated pylint workflow (targeting Python 3.8-3.10 when the project requires 3.12) suggests CI maintenance is not prioritized. For an evaluation context, this means there is no automated quality assurance visible to external stakeholders.
