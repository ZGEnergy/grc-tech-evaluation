# Observation: Clean Contingency Sweep API Without Reconstruction

**Test:** A-7 (N-M Contingency Sweep)
**Dimension:** expressiveness
**Tool:** pypsa 1.1.2

## Finding

PyPSA provides all three primitives needed for the contingency sweep without
any workarounds:

1. **Graph access:** `net.graph()` returns a NetworkX OrderedGraph directly.
   No export/conversion needed. `graph(include_inactive=False)` respects
   branch active flags.

2. **In-place branch toggling:** Setting `net.lines.at[name, "active"] = False`
   disables a branch without model reconstruction. `net.lpf()` re-solves the
   DCPF on the modified network.

3. **Connectivity checking:** `nx.connected_components(net.graph(include_inactive=False))`
   identifies islanded components after outages.

The full N-M sweep with escalating pruning (266 cases across N-1, N-2, N-3) was
implemented in ~140 lines of user code (excluding boilerplate), with zero
workarounds. The API surface is precisely what you'd want for this use case.

## Implication

Strong evidence for PyPSA expressiveness in contingency analysis. The combination
of native NetworkX graph, in-place modification, and lightweight `lpf()` re-solve
makes contingency workflows natural. The 97ms per-case average on TINY suggests
the overhead is in PyPSA's lpf() setup rather than the solve itself.
