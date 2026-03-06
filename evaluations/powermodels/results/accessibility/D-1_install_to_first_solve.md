---
test_id: D-1
tool: powermodels
dimension: accessibility
status: qualified_pass
timestamp: 2026-03-05
---

# D-1: Install-to-First-Solve Wall-Clock Time

## Finding

PowerModels achieves a two-line parse-and-solve workflow with clean dependency resolution, but Julia's JIT compilation imposes a ~1.5s startup tax on every cold invocation -- roughly 3x slower than Python equivalents for the same trivial DCPF.

## Evidence

### Install process (from notes/install-findings.md)

`Pkg.instantiate()` resolved all dependencies on the first attempt with no version conflicts, no UUID issues, and no compat workarounds. This was the cleanest install of all six tools evaluated. The `Project.toml` [compat] bounds are well-maintained upstream. No system-level dependencies required -- all solvers (HiGHS, Ipopt, SCIP) are installed as Julia packages with precompiled JLL binaries.

### Cold-start timing (fresh Julia process)

```

Package load time: 0.97s - 0.99s
First-solve time (incl. parse + JIT): 0.46s - 0.55s
Total wall-clock: 1.45s - 1.52s

```

Two consecutive runs measured. The variation is small, indicating stable performance after precompilation.

### API surface for first solve

```julia
using PowerModels
result = compute_dc_pf(parse_file("/workspace/data/networks/case39.m"))

```

Two lines: parse file, solve. The result is a dictionary with clear keys (`termination_status`, `objective`, `solution`, `solve_time`). The solution is nested under `result["solution"]["bus"]` -- not at the top level, which caused an initial KeyError when following the test specification's suggested access pattern (`result["bus"]`). This is a minor discoverability issue.

### Informative warnings

The tool emits 92 warnings about tightening angle limits on all 46 branches (angmin and angmax), e.g.:

```

[warn | PowerModels]: this code only supports angmin values in -90 deg. to 90 deg.,

tightening the value on branch 32 from -360.0 to -60.0 deg.

```

These are good engineering practice (explicit about data modifications) but verbose -- they dominate the console output and could obscure actual errors.

### Issues encountered

1. **Result key confusion:** The result dict nests bus data under `result["solution"]["bus"]`, not `result["bus"]`. The test spec's suggested code fails with a `KeyError`. This is a documentation/discoverability issue.
2. **Warning verbosity:** 92 warning lines for a 39-bus case make it hard to see actual output. No option to suppress or aggregate warnings is immediately obvious.
3. **No issues with dependency resolution, file parsing, or solver execution.**

## Implications

Install experience is excellent -- the cleanest of the six tools. The two-line API is minimal and the solver is explicit (no global state). However, the ~1.5s cold-start time is a known Julia limitation that affects iterative workflows (users are expected to stay in the REPL). The nested result dict structure and warning verbosity are minor friction points. Overall, a strong accessibility story for users willing to adopt the Julia REPL workflow, but the JIT tax penalizes scripted/CI use cases.
