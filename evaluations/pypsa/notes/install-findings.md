# PyPSA — Install & Smoke-Test Findings

**Date:** 2026-03-03
**Version resolved:** pypsa 1.1.2, pandapower 3.4.0, matpowercaseframes 2.0.1
**Script:** [`../verify_install.py`](../verify_install.py)

## Summary

DCPF on IEEE 39-bus completed successfully via `net.lpf()` (linear power flow).
However, reaching that point required two workarounds for broken import paths.

## Findings

### [accessibility] No native MATPOWER .m file reader

PyPSA cannot load `.m` files on its own. It relies on pandapower as an
intermediary, which creates a hard dependency on a competing tool just for
data I/O. This is a friction point for any workflow that starts from standard
IEEE/MATPOWER test cases.

The two import paths available:

1. **`import_from_pandapower_net(net_pp)`** — Crashes on case39 with a shape
   mismatch in the `v_mag_pu_set` assignment (bus count vs generator count
   broadcast failure in `pypsa/network/io.py:2265`). This is a bug in PyPSA
   1.1.2's pandapower importer — it assumes generator buses are unique but
   case39 has multiple generators at bus 31.

2. **`import_from_pypower_ppc(ppc)`** — Works, but requires manually
   constructing a pypower-format dict from `matpowercaseframes`. This is the
   path we use. It emits warnings about unsupported features (areas, gencosts,
   component status).

**Rubric relevance:** Accessibility (API friction), Maturity (broken converter
that ships in the release).

### [maturity] Broken pandapower converter ships in release

The `import_from_pandapower_net` method has been broken since at least PyPSA
1.1.x on any network where multiple generators share a bus. This is a
standard topology (case39 bus 31 has the slack generator). The fact that this
ships unfixed in a release suggests the pandapower import path is not tested
in CI against reference cases.

### [supply_chain] Transitive dependency on pandapower for I/O

Even using the pypower path, we still need `matpowercaseframes` (a third-party
package) to parse `.m` files. The full dependency chain for loading a standard
test case: `pypsa` → `matpowercaseframes` → `.m` file. Compare to PowerModels.jl
or MATPOWER which parse `.m` files natively with zero extra dependencies.

### [accessibility] API is clean once data is loaded

Once you have a `Network` object, the API is straightforward:

```python
net.lpf()  # DC power flow (linear power flow)
```

No options objects, no solver selection needed for DCPF. This is a positive
signal for the core API design.

### [gate] DCPF passes

39 buses, 35 lines (pandapower splits some branches into transformers),
linear power flow converges. The tool can solve DC power flow on standard
test cases.
