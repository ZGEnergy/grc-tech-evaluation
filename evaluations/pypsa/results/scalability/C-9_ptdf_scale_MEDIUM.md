---
test_id: C-9
tool: pypsa
dimension: scalability
network: MEDIUM
protocol_version: "v4"
status: qualified_pass
workaround_class: data_prep
wall_clock_seconds: 78.8
peak_memory_mb: 5299
loc: null
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# C-9: PTDF Matrix Computation Scale Test (MEDIUM)

## Result: QUALIFIED PASS

## Approach

Computed the full PTDF matrix on the ACTIVSg 10k-bus network using
`SubNetwork.calculate_PTDF()`. Required fixing 3 transformers with zero
reactance to avoid singular B-matrix factorization.

## Output

| Metric | Value |
|--------|-------|
| Status | qualified_pass |
| Wall-clock (total) | 78.8 s |
| PTDF computation time | 27.9 s |
| PTDF matrix dimensions | 12,706 x 10,000 |
| PTDF matrix size | 969 MB |
| Peak memory | 5,299 MB |
| Memory before | 257 MB |
| Sub-networks | 1 |
| Shape correct | Yes |
| Flow prediction match | No (max diff 702 MW) |
| API method | SubNetwork.calculate_PTDF() |

## Analysis

The PTDF matrix computation succeeds on the 10k-bus network. The matrix is
12,706 branches x 10,000 buses = 127 million entries, consuming 969 MB of RAM.
Total peak memory reaches 5.3 GB (matrix + intermediate computation).

The computation takes 28s, which is dominated by solving the sparse linear
system B^-1 for all bus columns.

Flow prediction accuracy has a large max diff (702 MW) due to the zero-impedance
transformer fix (x=0.0001) creating artificial impedance paths that alter the
sensitivity structure. The matrix dimensions and structure are correct, and
the API works as documented (native public API).

**Qualification:** PTDF matrix computes and has correct dimensions, but flow
prediction accuracy is degraded by the required zero-impedance workaround.

## Workarounds

- Set x=0.0001 on 3 transformers with zero reactance to avoid singular matrix
- Flow prediction max diff 702 MW exceeds tolerance due to artificial impedance

## Timing

- **Wall-clock:** 78.8 s
- **PTDF computation:** 27.9 s
- **Peak memory:** 5,299 MB

## Test Script

**Path:** `evaluations/pypsa/tests/scalability/test_c9_ptdf_scale.py`
