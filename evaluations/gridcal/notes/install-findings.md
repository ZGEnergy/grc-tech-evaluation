# GridCal (VeraGrid) — Install & Smoke-Test Findings

**Date:** 2026-03-03
**Version resolved:** veragridengine 5.6.28
**Script:** [`../verify_install.py`](../verify_install.py)

## Summary

DCPF on IEEE 39-bus completed successfully. Converged with 39 buses, 46
branches. But reaching a working install surfaced serious supply chain and
maturity concerns.

## Findings

### [supply_chain] Package renamed without migration path — GridCalEngine → VeraGridEngine

The project has been renamed from GridCal to VeraGrid. The PyPI package
`GridCalEngine` still installs (v5.4.1) but prints a deprecation notice
on every import:

```
GridCal has changed name to VeraGrid.
The gridcal package cannot be updated anymore, instead install
the also free and open source 'veragrid' witch is just the new name
of the software.
```

The new package is `veragridengine` on PyPI (import as `VeraGridEngine`).
This is a hard rename — not an alias, not a compatibility shim. Code written
against `GridCalEngine` will break on the next version. The deprecation
message has a typo ("witch" instead of "which"), which is a minor but
telling quality signal.

**Rubric relevance:** Supply Chain (naming instability, no migration path),
Maturity (typo in user-facing deprecation message).

### [supply_chain] No `__version__` attribute

`VeraGridEngine.__version__` raises `AttributeError`. Version must be
retrieved via `importlib.metadata.version("veragridengine")`. This is a
minor packaging deficiency but unusual for a mature Python package.

### [accessibility] DC power flow requires non-obvious enum

There is no `EngineType.DC` — the DC power flow is invoked via:

```python
from VeraGridEngine.enumerations import SolverType
opts = vge.PowerFlowOptions(solver_type=SolverType.Linear)
results = vge.power_flow(grid, options=opts)
```

The available `EngineType` values are: `Bentayga`, `GSLV`, `NewtonPA`,
`PGM`, `VeraGrid`. The available `SolverType` values for DC-like analysis
are: `Linear`, `LACPF`. Neither "DC" nor "DCPF" appears anywhere in the
enum names. A user looking for "DC power flow" will not find it without
reading source code or trial-and-error.

**Rubric relevance:** Accessibility (discoverability of standard operations).

### [accessibility] Native .m file reader works well

```python
grid = vge.open_file("case39.m")
```

One function, no extra dependencies, handles MATPOWER format natively.
This is the cleanest `.m` import of any Python tool evaluated.

### [supply_chain] urllib3/chardet version conflict warning

Every import produces:

```
RequestsDependencyWarning: urllib3 (2.6.3) or chardet (6.0.0.post1)/
charset_normalizer (3.4.4) doesn't match a supported version!
```

This indicates unpinned or loosely-pinned transitive dependencies that
have drifted out of the `requests` library's supported range. Not a
functional issue but a packaging hygiene signal.

### [gate] DCPF passes

39 buses, 46 branches (preserves all branches unlike pandapower's
transformer splitting), converged. Full branch count matches MATPOWER.
