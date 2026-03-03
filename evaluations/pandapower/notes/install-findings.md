# pandapower — Install & Smoke-Test Findings

**Date:** 2026-03-03
**Version resolved:** pandapower 3.4.0, matpowercaseframes 2.0.1
**Script:** [`../verify_install.py`](../verify_install.py)

## Summary

DCPF on IEEE 39-bus completed successfully. Converged with 39 buses, 35 lines.
The `.m` file loading works but required an undocumented extra dependency.

## Findings

### [accessibility] MATPOWER .m import requires undocumented dependency

`pandapower.converter.from_mpc()` is the documented way to load MATPOWER
files, but calling it on a `.m` file raises:

```
NotImplementedError: matpowercaseframes is used to convert .m file.
Please install that python package.
```

The `matpowercaseframes` package is not declared as a dependency of
pandapower — it's an optional requirement that only surfaces at runtime.
The `[performance]` extra doesn't include it either. For `.mat` (binary
MATLAB) files, scipy is used and works without extras.

**Rubric relevance:** Accessibility (undocumented dependency for standard
workflow), Supply Chain (hidden transitive dependency).

### [accessibility] Nested converter import path

The documented API `pp.converter.from_mpc()` does not work in pandapower
3.4.0. The actual import path is:

```python
from pandapower.converter.matpower.from_mpc import from_mpc
```

The top-level `pandapower.converter` namespace does not re-export this
function. This is a minor API design issue — users following docs or
tutorials will hit an `AttributeError`.

### [maturity] Warning about transformer detection

Loading case39 emits:
```
There are 11 branches which are considered as trafos — due to ratio
unequal 0 or 1 — but connect same voltage levels.
```

This is a known behavior where pandapower's MATPOWER converter
interprets tap-changing branches as transformers even when voltage levels
match. The 39-bus case has 46 branches total but pandapower reports only
35 lines (the other 11 become trafos). This affects branch counts when
comparing across tools.

### [gate] DCPF passes

`pp.rundcpp(net)` converges on case39. The API is one function call.
Clean and functional.

### [accessibility] Simple, clean power flow API

```python
pp.rundcpp(net)  # DC power flow
print(net.converged)
```

Convergence status is a property on the network object. Results are
accessible via `net.res_bus`, `net.res_line`, etc. This is a well-designed
interface for basic power flow.
