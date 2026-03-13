---
test_id: B-3
tool: pypsa
dimension: extensibility
network: TINY
protocol_version: v9
skill_version: v1
test_hash: bcf1db83
status: qualified_pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 0.144
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 184
solver: null
timestamp: 2026-03-11T00:00:00Z
---

# B-3: Contingency Loop — N-1 without base model reconstruction

## Result: QUALIFIED PASS

## Approach

The intended API `n.lpf_contingency()` is broken on Python 3.12+. Instead, used PyPSA's native `sub_network.calculate_BODF()` method to compute the Branch Outage Distribution Factor matrix analytically, then evaluated all 46 N-1 contingencies via a pure matrix computation loop — no per-iteration re-solves and no file re-reads.

**Sequence:**
1. Load network once; run `n.lpf()` for base case
2. `n.determine_network_topology()` — builds SubNetwork
3. `sn.calculate_PTDF()` — required prerequisite for BODF
4. `sn.calculate_BODF()` — computes 46×46 BODF matrix
5. Loop over each branch j: `post_flows = base_flows + BODF[:, j] * base_flows[j]`
6. Record max loading per contingency

The model object is never re-read from file. Base case flows are assembled once from `n.lines_t.p0` and `n.transformers_t.p0`. All 46 contingency calculations are pure numpy operations on the precomputed BODF matrix.

## Output

| Metric | Value |
|--------|-------|
| Branches analyzed (N-1) | 46 |
| BODF matrix shape | 46 × 46 |
| Contingency loop time | 0.00026 s |
| Base flow max | 830.0 MW |
| File re-reads in loop | 0 |

**Top 5 worst contingencies by max post-contingency flow:**

| Rank | Outaged Branch | Max Post-Flow (MW) | Most Loaded Branch |
|------|---------------|-------------------|-------------------|
| 1 | Line:L21 | 1290.0 MW | Transformer:T10 |
| 2 | Transformer:T1 | 963.2 MW | Line:L11 |
| 3 | Line:L26 | 962.5 MW | Line:L28 |
| 4 | Line:L28 | 962.5 MW | Line:L26 |
| 5 | Line:L10 | 931.5 MW | Line:L8 |

## Workarounds

- **What:** Used `sub_network.calculate_BODF()` (native PyPSA method) instead of `n.lpf_contingency()`.
- **Why:** `n.lpf_contingency()` is broken on Python 3.12+ (known upstream bug, unfixed as of PyPSA 1.1.2). The BODF method is a documented public API method on `SubNetwork` that achieves the same result analytically.
- **Durability:** stable — `calculate_BODF()` is a public, documented method present in PyPSA's official API. It is explicitly listed in the SubNetwork API and has been stable across recent versions.
- **Grade impact:** B-level. The pass condition is met (no file re-reads, in-memory loop). The workaround is a more efficient alternative than the broken `lpf_contingency()` — it uses a documented public API and produces analytically exact results.
- **Version tested:** PyPSA 1.1.2

## Timing

- **Wall-clock:** 0.144 s (includes network loading and PTDF/BODF matrix build; contingency loop alone: 0.00026 s)
- **Timing source:** measured
- **Peak memory:** not measured
- **BODF computation method:** analytical (no per-iteration solves)

## Test Script

**Path:** `evaluations/pypsa/tests/extensibility/test_b3_contingency_loop_tiny.py`

Key API sequence:
```python
n.lpf()                             # base case
n.determine_network_topology()
sn = n.sub_networks.at["0", "obj"]
sn.calculate_PTDF()                 # required prerequisite
sn.calculate_BODF()                 # native PyPSA: 46x46 matrix
BODF = sn.BODF
# Loop — no file re-read:
for j in range(n_branches):
    post_flows = base_flows + BODF[:, j] * base_flows[j]
    max_loading = abs(post_flows).max()
```
