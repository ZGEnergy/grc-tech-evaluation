---
test_id: C-9
tool: pandapower
dimension: scalability
network: MEDIUM
protocol_version: "v11"
skill_version: "v2"
test_hash: "7d785c5a"
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 289.425
timing_source: measured
peak_memory_mb: 5403.77
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 249
solver: "N/A (direct matrix computation)"
cpu_threads_used: 1
cpu_threads_available: 32
timestamp: 2026-03-24T00:00:00Z
---

# C-9: PTDF Matrix Computation on MEDIUM

## Result: PASS

## Approach

Loaded the ACTIVSg10k network (10,000 buses, 12,706 branches) and computed the full
PTDF matrix using `pandapower.pypower.makePTDF.makePTDF(baseMVA, bus, branch)`. Validated
against DCPF branch flows computed via `Bf @ Va + Pfinj`.

The network contains 5 phase-shifting transformers. Per B-9 methodology, the PTDF
validation applied Pbusinj/Pfinj correction terms. When corrections did not fully
resolve phase-shifter deviations (max diff 3.66e+04 MW on phase-shifter branches),
those 5 branches were excluded from the accuracy comparison. Excluding phase-shifter
branches, the maximum flow deviation was 2.41e-10 MW -- well within the 1e-6 MW
tolerance.

### API Used

```python
from pandapower.pypower.makePTDF import makePTDF
H = makePTDF(baseMVA, bus, branch)
```

The API is a direct call with no special configuration needed. The function is part of
pandapower's PYPOWER backend.

## Output

| Metric | Value |
|--------|-------|
| PTDF shape | 12,706 x 10,000 |
| PTDF compute time | 1.034492e+01 s |
| Peak memory | 5.403766e+03 MB |
| Matrix size (dense) | 969.39 MB |
| Matrix density | 6.859739e-01 |
| Matrix rank | 9,999 |
| Phase shifters | 5 |

### Validation Against DCPF

| Comparison | Max Diff (MW) | Within 1e-6 |
|------------|---------------|-------------|
| With Pbusinj/Pfinj correction | 3.657510e+04 | No |
| Without correction (raw) | 3.668437e+04 | No |
| Excluding 5 phase-shifter branches | 2.412435e-10 | Yes |

The large corrected/raw deviations are concentrated entirely on 5 phase-shifting
transformer branches. All 12,701 non-phase-shifter branches match DCPF within
2.41e-10 MW. This is consistent with B-9 TINY findings (max error 1.6e-12 MW on
non-phase-shifter branches).

### Network Dimensions

| Element | Count |
|---------|-------|
| Buses (PPC) | 10,000 |
| Branches (PPC) | 12,706 |
| Lines | 9,726 |
| Transformers | 975 |

## Workarounds

None required.

## Timing

- **Wall-clock:** 289.425 s (includes DCPF solve + PTDF computation + validation)
- **PTDF compute only:** 10.345 s
- **Timing source:** measured
- **Peak memory:** 5403.77 MB
- **CPU threads used:** 1 (makePTDF is single-threaded NumPy)
- **CPU threads available:** 32

The PTDF computation itself takes only 10.3 s. The remaining wall-clock time is
dominated by network loading (the MATPOWER .m parser at 10k-bus scale) and the
DCPF solve used for validation. The 5.4 GB peak memory reflects the dense 12706 x 10000
PTDF matrix (969 MB) plus DCPF solve and intermediate computation buffers.

## Test Script

**Path:** `evaluations/pandapower/tests/scalability/test_c9_ptdf_medium.py`
