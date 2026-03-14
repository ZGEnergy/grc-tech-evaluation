---
test_id: D-1
tool: pypsa
dimension: accessibility
network: N/A
status: pass
workaround_class: null
timestamp: 2026-03-13T12:00:00Z
protocol_version: v10
skill_version: v1
test_hash: caa92843
---

# D-1: Install-to-First-Solve Time

## Summary

PyPSA installs quickly via `uv sync` and reaches a first successful solve in under
2 seconds wall-clock time. The install-to-first-solve experience is frictionless for
Python-literate users.

## Install Process

1. **Dependency resolution:** `uv sync` in the devcontainer. With a warm cache, this
   completes in 0.01s (90 packages resolved, 88 audited). On a cold install, `uv sync`
   resolves and installs PyPSA v1.1.2 plus 88 transitive dependencies.

2. **No compiled extensions required:** PyPSA is pure Python with numpy/scipy/pandas
   as compiled dependencies. These are pre-built wheels, so no compiler toolchain is
   needed.

3. **Solver bundled:** HiGHS (LP/MILP/QP) is installed via the `highspy` pip package.
   No separate solver installation or license management required.

## First-Solve Timing

| Step | Wall-Clock Time |
|------|----------------|
| `import pypsa` | 1.094s |
| Load case39 via shared loader | 0.049s |
| `n.lpf()` (DCPF solve) | 0.060s |
| **Total** | **1.203s** |

A minimal 2-bus OPF from scratch (no MATPOWER loading) completes in 1.370s total
(1.109s import + 0.260s model build + solve).

## Friction Points

1. **FutureWarning on optimize():** Every call to `n.optimize()` emits a
   `FutureWarning` about `include_objective_constant` changing default in v2.0.
   This is informational noise that may confuse new users but does not block
   functionality.

2. **Carrier warnings:** Adding components without explicit `carrier` attributes
   produces warnings suggesting `n.sanitize()`. These are non-blocking but add
   visual noise to the first experience.

3. **Shadow price warning:** After every `optimize()` call, a log message states
   "The shadow-prices of the constraints ... were not assigned to the network."
   This is confusing for users who expect shadow prices to be available on the
   network object after solving (see observation api-friction A-3).

4. **MATPOWER loading warnings:** The shared loader path emits warnings about
   unsupported PYPOWER features (areas, gencosts, component status) and about
   the `status` attribute name being misleading.

## Assessment

The install process has zero friction: `uv sync` handles everything, including the
solver. The first solve completes in ~1.2 seconds. The only friction is cosmetic
(verbose warnings), not functional. No source code reading, no manual configuration,
and no external downloads are required to go from zero to a working power flow solve.
