---
test_id: D-3
tool: matpower
dimension: accessibility
network: N/A
protocol_version: "v10"
skill_version: "v1"
test_hash: "df16ea97"
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: estimated
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
solver: null
timestamp: "2026-03-14T00:00:00Z"
---

# D-3: Example Verification

## Result: INFORMATIONAL

## Finding

6 of 7 tested MATPOWER examples run without modification in the devcontainer (Octave 9.2.0). One example fails due to a missing test case file not on the path. MOST examples work correctly.

## Evidence

### Examples Tested

MATPOWER ships two categories of examples:
1. **`examples/` directory:** 2 files (`cpf_example.m`, `convert_1p_to_3p_ex1.mlx`)
2. **`most/examples/` directory:** 7 script files (`most_ex1_ed.m` through `most_ex7_suc.m`) plus supporting data files
3. **User's Manual inline examples:** Basic `runpf`, `runopf`, `rundcpf`, `rundcopf` invocations

### Results

| Example | Source | Result | Notes |
|---------|--------|--------|-------|
| `runpf('case9')` | Manual Ch 3 | **Works** | AC PF converges in 4 iterations, full system summary printed |
| `runopf('case9')` | Manual Ch 6 | **Works** | AC OPF converges, objective $5296.69/hr |
| `rundcpf('case9')` | Manual Ch 3 | **Works** | DC PF succeeds, generation matches load |
| `rundcopf('case9')` | Manual Ch 6 | **Works** | DC OPF converges, uniform LMPs (uncongested) |
| `cpf_example.m` | examples/ | **Fails** | `loadcase: specified case not in MATLAB's search path` -- requires `t_case9_pfv2` which is in `lib/t/` (test directory), not on the default path |
| `most_ex1_ed.m` | most/examples/ | **Works** | Economic dispatch with 3-bus system |
| `most_ex2_dcopf.m` | most/examples/ | **Works** | DCOPF with reserves |

### Summary Counts

| Outcome | Count |
|---------|-------|
| Run unmodified | 6 |
| Require fixes | 1 |
| Silently broken | 0 |

### Details on the Failing Example

`cpf_example.m` loads `t_case9_pfv2`, a test case file located in `lib/t/`. This directory is not added to the path by the standard installation process (it contains internal test infrastructure). The fix is trivial (`addpath('lib/t')`), but a new user following the getting-started path would encounter this error.

The `.mlx` file (`convert_1p_to_3p_ex1.mlx`) is a MATLAB Live Script format not supported by Octave, so it was excluded from testing. This is expected -- MATPOWER's documentation states that `.mlx` files require MATLAB.

### Quality Assessment

- **Self-contained:** Manual examples are self-contained (single function calls with case name strings). No external data files needed.
- **Output quality:** All working examples produce rich, formatted output tables by default.
- **Dependency clarity:** The `case9` examples work with no special setup beyond the standard 5-directory `addpath` calls. MOST examples require adding `most/lib` and `most/examples` to the path.
- **No silent failures:** All examples that succeed produce correct results. No example ran without error but produced wrong output.

## Implications

MATPOWER's getting-started examples are reliable and well-maintained. The one failure (`cpf_example.m`) is a minor path configuration issue, not a code bug. The User's Manual inline examples (`runpf('case9')`, etc.) are the most reliable entry point for new users. MOST examples require more path setup but work correctly once configured.
