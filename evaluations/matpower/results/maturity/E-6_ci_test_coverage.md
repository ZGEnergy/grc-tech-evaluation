---
test_id: E-6
tool: matpower
dimension: maturity
network: N/A
protocol_version: "v4"
status: informational
workaround_class: null
timestamp: "2026-03-06T14:00:00Z"
---

# E-6: CI / Test Coverage

## CI Configuration

**File:** `.github/workflows/continuous-integration.yml`
**Platform:** GitHub Actions

### Build Matrix

| Platform | OS | Status |
|----------|-----|--------|
| Octave | macOS-latest | Active |
| Octave | ubuntu-22.04 | Active |
| Octave | ubuntu-24.04 | Active |
| MATLAB | ubuntu-latest | Active |

### CI Pipeline Steps

1. Checkout repository
2. Install Octave (or MATLAB via `matlab-actions/setup-matlab`)
3. Build/cache IPOPT MEX interface (optional)
4. Build/cache OSQP interface (optional, Ubuntu only)
5. Install MATPOWER (`install_matpower(0,1,1)`)
6. Verify solver availability (GLPK, IPOPT, OSQP)
7. Run test suites:
   - `test_mptest(0,1)` — MPTEST framework tests
   - `test_mips(0,1)` — MIPS solver tests
   - `test_mp_opt_model(0,1)` — MP-Opt-Model tests
   - `test_matpower(0,1)` — Core MATPOWER tests
   - `test_most(0,1)` — MOST scheduling tests
   - `test_matpower(0,1)` with legacy mode — Legacy framework tests (when MP-Core available)

### Trigger

- On every push (all branches)
- Manual workflow dispatch

## Test Suite

### Test File Count

**462 test files** (`t_*.m`) found across the MATPOWER 8.1 distribution.

### Test Suites

| Suite | Command | Scope |
|-------|---------|-------|
| MPTEST | `test_mptest` | Test framework infrastructure |
| MIPS | `test_mips` | Interior point solver |
| MP-Opt-Model | `test_mp_opt_model` | Optimization model layer |
| MATPOWER | `test_matpower` | Core PF/OPF/CPF functionality |
| MOST | `test_most` | Multi-period scheduling |

### Coverage Assessment

- **No formal code coverage metrics.** Neither MATLAB nor Octave has standard
  coverage tools integrated into CI. No coverage reports are generated.
- **Extensive functional test suite.** 462 test files covering all major
  functionality: power flow (AC/DC), OPF (AC/DC), CPF, sensitivity analysis,
  case format conversion, and MOST scheduling.
- **Solver-specific tests.** CI verifies GLPK, IPOPT, and OSQP availability
  and runs solver-specific test paths.
- **Cross-platform validation.** Tests run on macOS + two Ubuntu versions +
  MATLAB, catching platform-specific issues (e.g., #274: DC OPF test failure
  with MATLAB R2025b linprog).

## MPTEST Framework

MATPOWER uses its own test framework (MPTEST) rather than a standard testing
library. Key functions:
- `t_begin(num_tests, quiet)` — declare test count
- `t_ok(condition, msg)` — boolean assertion
- `t_is(got, expected, prec, msg)` — numeric comparison with precision
- `t_skip(count, msg)` — skip tests (e.g., missing solver)
- `t_end()` — summary

## Assessment

| Aspect | Rating | Notes |
|--------|--------|-------|
| CI exists | YES | GitHub Actions, runs on every push |
| Cross-platform | YES | macOS, Ubuntu 22.04, Ubuntu 24.04, MATLAB |
| Test suite size | LARGE | 462 test files |
| Code coverage metric | NO | No coverage measurement |
| Test framework | Custom | MPTEST (simple but functional) |
| Solver integration tests | YES | GLPK, IPOPT, OSQP verified |
| Regression tests | YES | Comprehensive numerical comparison tests |

The CI is well-designed for a MATLAB/Octave project. The main gap is the absence
of code coverage measurement, though this is common in the MATLAB ecosystem.
The test suite is extensive and catches real regressions (evidence: issues #274,
\#275 caught by CI on new MATLAB/Octave versions).
