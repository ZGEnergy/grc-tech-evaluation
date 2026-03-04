# Observation: PyPSA 1.1.2 Scenario + Pypower Import Bug

**Test:** A-8 (Stochastic Timeseries)
**Dimension:** expressiveness
**Tool:** pypsa 1.1.2

## Finding

PyPSA 1.1.2 has a bug in `SubNetwork.find_bus_controls()` that prevents
`net.optimize()` from working on scenario-enabled networks imported via
`import_from_pypower_ppc()`. The bug manifests as:

```
KeyError: "Index(['30', '32', ...] not in index"
```

**Root cause:** After `set_scenarios()`, the buses DataFrame index becomes a
MultiIndex of (scenario, bus_name). However, `find_bus_controls()` attempts to
look up buses using their original non-scenario index (e.g., "30" instead of
("low", "30")), causing the KeyError.

**Workaround:** Monkey-patching `SubNetwork.find_bus_controls = lambda self: None`
is safe for DC OPF since PV/PQ classification only matters for AC power flow.
This is classified as **fragile** because it depends on an internal method.

**Additional bug:** `net.get_scenario()` fails with `TypeError: cannot pickle
'Highs' object` when the HiGHS solver model is attached to the network after
optimization. This prevents clean extraction of per-scenario sub-networks.
Per-scenario results can be extracted directly from the MultiIndex-columned
DataFrames in `generators_t.p` as a workaround.

## Implication

The `set_scenarios()` API is well-designed and genuinely useful for stochastic
optimization, but its interaction with the legacy pypower importer is buggy in
version 1.1.2. Networks built natively in PyPSA (using `net.add()` calls rather
than pypower import) would likely avoid this issue. This is a maturity issue
rather than an architectural limitation.
