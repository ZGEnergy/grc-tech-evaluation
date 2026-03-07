---
test_id: D-1
tool: pypsa
dimension: accessibility
network: N/A
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: null
peak_memory_mb: null
loc: null
solver: highs
timestamp: 2026-03-06T00:00:00Z
---

# D-1: Install to First Solve

## Objective

Assess how quickly a new user can go from zero to a working power-system solve
using PyPSA.

## Installation Process

PyPSA supports three package managers with one-command installs:

| Manager | Command |
|---------|---------|
| pip | `pip install pypsa` |
| conda | `conda install -c conda-forge pypsa` |
| uv | `uv add pypsa` |

The HiGHS LP/MIP solver ships as a default dependency, so no separate solver
installation is required. Python 3.11+ is the only prerequisite.

In this evaluation environment, `uv sync` resolved and installed PyPSA 1.1.2
plus all transitive dependencies with no manual intervention.

## Steps to First Solve

1. Install PyPSA (one command).
2. Write a minimal script: create Network, add Bus/Generator/Load, call
   `n.optimize()`.
3. Run it.

Total steps: **3**. No configuration files, no solver path setup, no license
keys.

## Verification

```
$ uv run python -c "import pypsa; print(pypsa.__version__)"
1.1.2
```

A 12-line script (create 2-bus network, 2 generators, 1 load, 1 line, call
`n.optimize()`) runs successfully and produces correct dispatch and bus marginal
prices on the first attempt.

## Documentation Quality for Install

The official docs at `docs.pypsa.org/latest` provide a clean installation page
listing all three package managers, optional extras (HDF5, Excel, mapping), and
solver guidance. Three quickstart notebooks are linked directly from the landing
page:

- Quickstart 1 -- Markets
- Quickstart 2 -- Power Flow
- Quickstart 3 -- Investments & Storage

## Minor Friction

- Running `n.optimize()` without setting `include_objective_constant` emits a
  `FutureWarning` about a default change in v2.0. Harmless but noisy for new
  users.
- Omitting `n.sanitize()` or carrier definitions triggers warnings about
  undefined carriers. These are cosmetic and do not affect correctness.

## Verdict

**PASS**. Single-command install with bundled solver. Three steps to first solve.
Comprehensive quickstart notebooks. No configuration hurdles.
