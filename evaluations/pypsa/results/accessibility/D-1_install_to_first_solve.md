---
test_id: D-1
tool: pypsa
dimension: accessibility
network: N/A
protocol_version: v11
skill_version: v2
test_hash: ef7694d3
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 6.96
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: null
solver: null
timestamp: 2026-03-24T18:30:00Z
---

# D-1: Install-to-First-Solve Time

## Result: PASS

## Finding

PyPSA installs in under 0.4 seconds via `uv sync` (cached wheels) and reaches a
first successful DCPF solve in under 7 seconds total wall-clock time. The
install-to-first-solve experience is frictionless for Python-literate users.

## Evidence

### Install Timing (measured)

Cold `uv sync` (fresh `.venv` creation, all wheels from local cache):

```
Resolved 90 packages in 0.57ms
real  0m0.385s
```

PyPSA v1.1.2 with 88 transitive dependencies. No compiled extensions beyond
pre-built wheels (numpy, scipy, pandas). HiGHS solver bundled via `highspy`.

Warm `uv sync` (existing `.venv`):

```
Resolved 90 packages in 0.57ms
Checked 88 packages in 0.79ms
real  0m0.013s
```

### First-Solve Timing (measured via `time.perf_counter()`)

Minimal 2-bus network with DCPF solve, measured across multiple runs after
cold venv creation:

| Run | Import (s) | Build (s) | Solve (s) | Total (s) |
|-----|-----------|-----------|-----------|-----------|
| 1 (first-ever, bytecode compile) | 19.35 | 0.48 | 0.18 | 20.01 |
| 2 (bytecode cached) | 5.69 | 0.10 | 0.16 | 5.96 |
| 3 (warm) | 6.46 | 0.14 | 0.17 | 6.77 |
| 4 (fully warm) | 1.26 | 0.04 | 0.05 | 1.34 |

Representative timing (runs 2-3, post-bytecode compilation): **~6.4s total**.
First-ever import includes Python bytecode compilation for 90 packages (~20s).
Fully warm process cache brings total under 1.4s.

### Friction Points (4 identified, all cosmetic)

1. **FutureWarning on `optimize()`:** Every call emits a `FutureWarning` about
   `include_objective_constant` changing default in v2.0. Informational noise.

2. **Carrier warnings:** Adding components without explicit `carrier` attributes
   produces warnings suggesting `n.sanitize()`. Non-blocking.

3. **Shadow price log message:** After every `optimize()` call, a log message
   states shadow prices "were not assigned to the network." Confusing for users
   who expect shadow prices on the network object after solving (see observation
   [api-friction A-3](../observations/api-friction-expressiveness-A-3_dcopf.md)).

4. **MATPOWER loading warnings:** The shared loader emits warnings about
   unsupported PYPOWER features and `status` attribute naming.

### Process Summary

The complete install-to-first-solve workflow requires:
- `uv sync` (one command, no manual configuration)
- `import pypsa` (one import)
- Build network + `n.lpf()` (standard Python API)

No compiler toolchain, no solver license, no external downloads, no manual
configuration files.

## Implications

PyPSA's install-to-first-solve time is excellent. The `uv sync` path handles
all dependencies including the solver. The first-ever import on a fresh venv
pays a one-time ~20s bytecode compilation tax, but subsequent runs are under 7s.
The only friction is cosmetic warnings, not functional blockers.
