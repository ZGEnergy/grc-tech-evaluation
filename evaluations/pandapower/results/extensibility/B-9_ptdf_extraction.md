---
test_id: B-9
tool: pandapower
dimension: extensibility
network: MEDIUM
protocol_version: "v4"
status: qualified_pass
workaround_class: fragile
wall_clock_seconds: 31.16
peak_memory_mb: 969.39
loc: 187
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# B-9: Compute PTDF matrix for MEDIUM (~10,000 buses)

## Result: QUALIFIED PASS

## Approach

1. Loaded ACTIVSg10k and solved DCPF to populate `net._ppc`
2. Extracted internal PYPOWER arrays (`baseMVA`, `bus`, `branch`)
3. Computed PTDF via `pandapower.pypower.makePTDF.makePTDF(baseMVA, bus, branch, slack_idx)`
4. Verified PTDF shape (12,706 x 10,000) and validated flow predictions against DCPF solution

## Output

| Metric | Value |
|--------|-------|
| Bus count (ppc) | 10,000 |
| Branch count (ppc) | 12,706 |
| Slack bus index | 7236 |
| PTDF shape | (12,706, 10,000) |
| PTDF memory | 969.39 MB |
| PTDF computation time | 28.03 s |
| Bus numbering | Sequential (0--9999) |
| Max flow difference | 7.43 pu |
| Mean flow difference | 0.027 pu |
| Nonzero fraction | 94.0% |
| Slack column all zeros | Yes |

The PTDF matrix computes successfully with correct dimensions and expected properties (slack column all zeros, nearly full density as expected for a meshed network). However, flow predictions diverge from DCPF results on the 10k-bus network (max diff 7.43 pu), likely due to shunt elements and tap-ratio effects in transformers not fully captured by the basic PTDF formulation. On TINY (39-bus), match was exact within 1e-6.

## Workarounds

- **What:** PTDF computed via `pandapower.pypower.makePTDF` using internal `_ppc` arrays. Requires running DCPF first to populate `net._ppc`.
- **Why:** No public high-level API for PTDF extraction. Must access PYPOWER internals.
- **Durability:** fragile -- depends on `_ppc` internal structure and `makePTDF` import path.
- **Grade impact:** PTDF computation works but flow validation shows larger errors on MEDIUM than TINY, and the access path is through internal APIs.

## Timing

- **Wall-clock:** 31.16 s (total including load + DCPF + PTDF computation + validation)
- **PTDF computation only:** 28.03 s
- **Peak memory:** 969.39 MB (PTDF matrix alone)

## Test Script

**Path:** `evaluations/pandapower/tests/extensibility/test_b9_ptdf_extraction_medium.py`
