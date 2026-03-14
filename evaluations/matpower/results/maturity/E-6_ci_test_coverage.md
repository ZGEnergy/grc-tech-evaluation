---
test_id: E-6
tool: matpower
dimension: maturity
network: N/A
protocol_version: "v10"
skill_version: "v1"
test_hash: "888c549c"
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

# E-6: CI/CD and Test Coverage

## Result: INFORMATIONAL

## Finding

MATPOWER has a comprehensive CI pipeline on GitHub Actions that tests across 4 OS/platform combinations (Octave on Ubuntu 22.04, Ubuntu 24.04, macOS; MATLAB on Ubuntu). The test suite uses MATPOWER's own mptest framework and covers all major subsystems: MIPS solver, MP-Opt-Model, MATPOWER core (both legacy and MP-Core frameworks), and MOST. CI runs on every push and is currently passing. No quantitative code coverage metric is published.

## Evidence

### CI configuration

Via `gh api repos/MATPOWER/matpower/actions/workflows`, accessed 2026-03-14:

- **Workflow:** "CI" (`.github/workflows/continuous-integration.yml`)
- **State:** active
- **Trigger:** push (all branches), manual dispatch

**Platform matrix:**

| Platform | OS | Status |
|----------|-----|--------|
| Octave | ubuntu-22.04 | Active |
| Octave | ubuntu-24.04 | Active |
| Octave | macos-latest | Active |
| MATLAB | ubuntu-latest | Active |

### Test suite structure

The CI workflow runs 5 test suites sequentially:

1. **test_mptest** -- Tests the test framework itself
2. **test_mips** -- Tests the MIPS (MATPOWER Interior Point Solver)
3. **test_mp_opt_model** -- Tests the optimization modeling layer
4. **test_matpower** -- Tests core MATPOWER functionality (PF, OPF, etc.)
5. **test_most** -- Tests the MOST (MATPOWER Optimal Scheduling Tool) extension

Additionally, when MP-Core is available:
6. **test_matpower (legacy mode)** -- Reruns with `have_feature('mp_core', 0)` to test backward compatibility

### Solver coverage in CI

The CI pipeline tests multiple solver integrations:
- **GLPK** -- Tested on Octave platforms
- **IPOPT** -- Tested on all platforms (built from source on macOS, package on Linux)
- **OSQP** -- Tested on Ubuntu platforms only
- **MATLAB Optimization Toolbox** -- Tested on MATLAB platform
- **MIPS** -- Built-in, always tested

### Recent CI runs

Via `gh api repos/MATPOWER/matpower/actions/runs`, accessed 2026-03-14:

| Date | Branch | Result |
|------|--------|--------|
| 2026-03-11 | master | success |
| 2026-03-11 | ci-testing | success |
| 2026-02-17 | master | success |
| 2026-02-17 | ci-testing | success |
| 2026-02-16 | master | success |

All recent runs are passing.

### Coverage metrics

No quantitative code coverage metric (e.g., line coverage percentage) is published or tracked. The mptest framework does not integrate with standard coverage tools like MATLAB's profiler-based coverage or Octave equivalents. Coverage assessment is qualitative: the test suite exercises PF, OPF, SCOPF, CPF, and multi-period scheduling across multiple solvers and network sizes, which suggests broad functional coverage.

### Architectural observation (consumed from B-6)

The B-6 code architecture audit found that MATPOWER runs its legacy test suite and its new MP-Core test suite in parallel during CI, ensuring backward compatibility. This dual-testing approach effectively doubles the functional coverage for core algorithms.

## Implications

MATPOWER's CI is well-structured for a MATLAB/Octave project: multi-platform, multi-solver, and consistently passing. The lack of quantitative coverage metrics is typical for MATLAB-ecosystem projects where standard coverage tooling is less mature than in Python/Julia ecosystems. The dual legacy/MP-Core testing is a strong quality signal. The main gap is the absence of HiGHS in CI (though HiGHS tests exist in the codebase and were added in November 2025 for Gurobi's PDHG solver comparison), and no SCIP testing.
