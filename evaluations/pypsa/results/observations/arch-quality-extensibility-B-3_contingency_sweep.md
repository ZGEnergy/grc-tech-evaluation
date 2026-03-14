---
tag: arch-quality
source_dimension: extensibility
source_test: B-3
tool: pypsa
severity: medium
timestamp: 2026-03-13T00:00:00Z
---

# Observation: n.copy() + n.lpf() contingency loop is 60ms per case on TINY

## Finding

PyPSA's `n.copy()` method creates a full in-memory clone of the network object, enabling N-M contingency sweeps without file re-reads. However, each copy + DCPF solve costs ~60ms per case on a 39-bus network, making it O(n_cases) rather than O(1) like the BODF-based analytical approach. For C(28,3) = 3,276 cases, total time was 195 seconds.

## Context

The B-3 test used graph-distance scoping (x=3) from bus 16 to identify 28 branches in scope, then enumerated all C(28,3) = 3,276 N-3 contingency cases. Each case required `n.copy()` + branch modification + `n.lpf()`. By contrast, the v9 script used `sub_network.calculate_BODF()` for analytical N-1 in sub-millisecond time per case.

## Implications

For scalability assessment: the n.copy() approach scales linearly with case count, which becomes expensive for large combinatorial sweeps. PyPSA does offer the BODF-based analytical approach for N-1, but extending it to N-M requires custom implementation. The architecture supports both approaches cleanly — the per-case overhead is in the DCPF solve, not in API friction.
