---
tag: solver-issues
source_dimension: scalability
source_test: C-5
tool: pypsa
severity: high
timestamp: 2026-03-04T22:10:00Z
---

# Observation: N-M contingency parameters don't scale to MEDIUM networks

## Finding

The eval-config specifies x=5 (graph distance) and m=4 (max outage order) for MEDIUM
network contingency sweeps (C-5). On the 10,000-bus ACTIVSg10k network, these parameters
produce a combinatorially infeasible number of contingency cases.

With x=5 on a dense 10k-bus network, the number of branches in scope is 200+, yielding
C(200,4) ≈ 64 million N-4 cases. Each case requires a sparse LU factorization (~6s
on this network per C-1). Even with aggressive pruning after lower-order sweeps, the
computation is intractable.

## Cross-Tool Implication

This is a **protocol issue, not a tool issue**. All six tools under evaluation will
face the same combinatorial explosion with these parameters on MEDIUM networks. The
parameters work on TINY (39-bus, x=3, m=3 → ~1,140 N-3 cases) but do not scale.

## Recommendation

For the evaluation protocol:
1. Scale contingency parameters by network size: x=2, m=2 for MEDIUM
2. Or add a max-cases cap (e.g., 10,000 total contingencies) with random sampling
3. Or use BODF/LODF-based screening instead of brute-force enumeration (though PyPSA's
   `lpf_contingency()` is broken in v1.1.2)
