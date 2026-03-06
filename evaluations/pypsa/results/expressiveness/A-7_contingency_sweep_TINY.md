# A-7: N-M Contingency Sweep (TINY)

- **Test ID:** A-7
- **Slug:** contingency_sweep
- **Tool:** PyPSA 1.1.2
- **Network:** IEEE 39-bus (case39.m)
- **Status:** PASS

## Pass Condition

Completes without full model reconstruction per contingency case. Load loss per contingency case collected. TINY: x=3 (graph distance), m=3 (max order).

## Results

| Metric | Value |
|--------|-------|
| Wall clock | 48.77 s |
| Total branches | 46 |
| Total cases evaluated | 617 |
| Total possible (no pruning/scoping) | 16261 |
| Pruning ratio | 96.2% |
| Cases with load loss | 35 |

### Cases per Order

| Order | Cases Evaluated | Pruned Branches |
|-------|----------------|-----------------|
| N-1 | 46 | 30 branches caused load loss |
| N-2 | 471 | (graph-distance scoped + pruning) |
| N-3 | 100 | (further pruning from N-2 results) |

### Method

- **Branch deactivation:** Toggle `n.lines.loc[br, "active"] = False` (no model reconstruction)
- **Graph-distance scoping:** NetworkX graph built from network topology; only branch combinations within x=3 hops evaluated
- **Pruning:** Branches whose N-1 removal causes load loss are excluded from higher-order combinations
- **Load loss detection:** NetworkX connected components on the active graph; loads in non-main islands counted as lost
- **Power flow:** `n.lpf()` per case for flow analysis

### Pruning Effectiveness

30 of 46 branches were pruned after N-1 analysis (their removal caused islanding/load loss). This reduced N-2 candidates from C(46,2)=1035 to C(16,2)=120 before graph-distance filtering, and N-3 from C(46,3)=15180 down to 100 cases.

## API

```python
# No built-in N-M sweep — manual implementation using:
n.lines.loc[br, "active"] = False  # deactivate branch
n.lpf()                             # re-solve (no reconstruction)
nx_graph = nx.Graph(...)            # or n.graph() for topology
```

## LOC

~120 lines (graph construction, distance scoping, pruning logic, sweep loop).

## Workarounds

1. **Manual sweep (stable):** PyPSA has no built-in N-M contingency sweep, but the API supports it cleanly via the `active` flag on branches and `n.lpf()`. NetworkX integration via `n.graph()` provides graph-distance scoping. No model reconstruction needed per case.

## Errors

None.
