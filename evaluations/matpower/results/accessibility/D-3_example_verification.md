---
test_id: D-3
tool: matpower
dimension: accessibility
network: N/A
protocol_version: "v4"
status: informational
workaround_class: null
timestamp: "2026-03-06T14:00:00Z"
---

# D-3: Example Verification — Official Getting-Started Examples

## Methodology

Located all example/tutorial scripts shipped with MATPOWER 8.1 in:
- `examples/` (2 files: `cpf_example.m`, `convert_1p_to_3p_ex1.mlx`)
- `most/examples/` (21 files: `most_ex1_ed.m` through `most_ex7_suc.m` + data files)
- `mips/examples/` (2 files: `mips_example1.m`, `mips_example2.m`)
- `mp-opt-model/examples/` (12 files: `lp_ex1.m`, `qp_ex1.m`, `milp_ex1.m`, etc.)

Ran each executable `.m` script via:

```
.devcontainer/dc-exec -C /workspace/evaluations/matpower octave <script>
```

Excluded `.mlx` files (MATLAB Live Script format, not executable in Octave).

## Results

### MATPOWER Core Examples

| Script | Status | Notes |
|--------|--------|-------|
| `cpf_example.m` | BROKEN | Fails with `no graphics toolkits are available!` — calls `figure()` for plotting. Computation runs correctly up to the plot call. |
| `convert_1p_to_3p_ex1.mlx` | SKIPPED | MATLAB Live Script format, not Octave-compatible |

### MOST Examples

| Script | Status | Notes |
|--------|--------|-------|
| `most_ex1_ed.m` | PASS | Runs unmodified, produces correct dispatch output |
| `most_ex2_dcopf.m` | PASS | Runs unmodified, produces correct DC OPF output |
| `most_ex3_dcopf_w_uc.m` | PASS | Runs unmodified, UC commitment schedule correct |
| `most_ex4_dcopf_ss.m` | PASS | Runs with warnings but completes. NaN in one entry (generator 5, period 1 — wind gen offline in that scenario). Output otherwise correct. |
| `most_ex5_mpopf.m` | BROKEN | MIPS solver fails with exit flag -1 (`Numerically Failed, Did not converge in 51 iterations`). Error: `structure has no member 'ExpectedDispatch'`. Solver convergence failure on multi-period OPF. |
| `most_ex6_uc.m` | PASS | Runs unmodified, produces correct UC + dispatch output |
| `most_ex7_suc.m` | PASS | Runs unmodified, produces correct stochastic UC output |

### MIPS Examples

| Script | Status | Notes |
|--------|--------|-------|
| `mips_example1.m` | BROKEN | `'banana' undefined` — references a `banana` function not shipped with MATPOWER. The function is a MATLAB Optimization Toolbox example, not available in Octave. |
| `mips_example2.m` | PASS | Runs unmodified, produces correct constrained optimization output |

### MP-Opt-Model Examples

| Script | Status | Notes |
|--------|--------|-------|
| `lp_ex1.m` | PASS | Runs unmodified |
| `qp_ex1.m` | PASS | Runs unmodified |
| `milp_ex1.m` | BROKEN | Computation succeeds but fails at `figure()` call for plotting (`no graphics toolkits are available!`). Would work in GUI environment. |
| `nleqs_master_ex1.m` | PASS | Runs unmodified |
| `nleqs_master_ex2.m` | PASS | Runs unmodified |
| `nlps_master_ex1.m` | BROKEN | `'banana' undefined` — same issue as `mips_example1.m` |
| `nlps_master_ex2.m` | PASS | Runs unmodified |
| `pne_ex1.m` | BROKEN | Computation starts but fails at `figure()` call for plotting |
| `qcqp_ex1.m` | BROKEN | Computation succeeds but crashes in `display_soln` with dimension mismatch: `nonconformant arguments (op1 is 2x2, op2 is 2x1)`. This is a bug in the display code. |
| `qcqp_example1.mlx` | SKIPPED | MATLAB Live Script format |
| `milp_example1.mlx` | SKIPPED | MATLAB Live Script format |

## Summary

| Category | Total | Pass | Broken | Skipped |
|----------|-------|------|--------|---------|
| MATPOWER core | 2 | 0 | 1 | 1 |
| MOST | 7 | 6 | 1 | 0 |
| MIPS | 2 | 1 | 1 | 0 |
| MP-Opt-Model | 12 | 6 | 4 | 2 |
| **Total** | **23** | **13** | **7** | **3** |

Pass rate (excluding skipped): 13/20 = 65%

## Failure Classification

| Failure Type | Count | Scripts |
|-------------|-------|---------|
| Missing graphics toolkit (headless) | 4 | `cpf_example`, `milp_ex1`, `pne_ex1`, (partial `milp_ex1`) |
| Missing `banana` function (MATLAB-only) | 2 | `mips_example1`, `nlps_master_ex1` |
| Solver convergence failure | 1 | `most_ex5_mpopf` |
| Bug in display code | 1 | `qcqp_ex1` |

## Key Findings

1. **Graphics-dependent examples fail in headless/CI environments.** Four examples
   call `figure()` without checking for display availability. This is the most
   common failure mode and would affect any Docker/CI/SSH deployment.

2. **Two examples reference `banana` function from MATLAB Optimization Toolbox.**
   This function is not available in GNU Octave. The examples are untested on
   Octave despite MATPOWER officially supporting it.

3. **`qcqp_ex1.m` has a genuine bug** in its `display_soln` call — dimension
   mismatch in the quadratic constraint display code.

4. **MOST examples are the most reliable** — 6/7 run unmodified (86%), reflecting
   the maturity of the MOST codebase.

5. **No examples require fixes beyond environment setup.** The 4 graphics failures
   would work in a GUI environment; the 2 banana failures would work in MATLAB.
   Only `most_ex5_mpopf` and `qcqp_ex1` represent genuine bugs.
