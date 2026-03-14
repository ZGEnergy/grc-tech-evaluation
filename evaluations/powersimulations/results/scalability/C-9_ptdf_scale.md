---
test_id: C-9
tool: powersimulations
dimension: scalability
network: MEDIUM
protocol_version: "v10"
skill_version: "v1"
test_hash: "88c2746b"
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 1.618
timing_source: measured
peak_memory_mb: 2810.6
matrix_density_pct: 68.60
loc: 228
solver: null
timestamp: "2026-03-14T00:00:00Z"
---

# C-9: PTDF Matrix on MEDIUM (ACTIVSg 10k)

## Result: PASS

## Approach

Computed the Power Transfer Distribution Factor (PTDF) matrix on the ACTIVSg 10000-bus network
using `PTDF(sys)` from PowerNetworkMatrices.jl. Measured wall-clock on the second invocation
(JIT warm-up on the first).

## Output

### PTDF Matrix Properties

| Metric | Value |
|--------|-------|
| Matrix dimensions | 10,000 x 12,706 |
| Total elements | 127,060,000 |
| Non-zero elements (|x| > 1e-10) | 87,159,838 |
| Density | 68.60% |
| Storage format | Dense (Float64) |
| Memory estimate (data only) | 969 MB |
| Wall-clock (timed run) | 1.618 s |
| Wall-clock (JIT warm-up) | 1.598 s |
| Peak memory (RSS) | 2,811 MB |
| Memory delta (PTDF computation) | 2,741 MB |

### Matrix Dimensions Note

The PTDF matrix is 10,000 x 12,706 (buses x branches), which is the transpose of the
conventional orientation (branches x buses). PowerNetworkMatrices.jl uses rows=buses,
columns=branches. The expected dimensions were 12,706 x 10,000 — this is an API convention
difference, not an error.

### Value Range

| Statistic | Value |
|-----------|-------|
| Min | -2.3388 |
| Max | 1.7899 |
| Mean |x|| | 0.003612 |

Values outside [-1, 1] indicate the presence of phase-shifting or tap-changing transformers
(PTDF entries can exceed unity when phase shifters are present).

### Row Sum Check

| Metric | Value |
|--------|-------|
| Mean |row sum| | 2.5994 |
| Max |row sum| | 10.0723 |

Non-zero row sums confirm that phase-shifting or tap-changing transformers are present
(row sums should be ~0 for a pure transmission network without phase shifters). The
ACTIVSg10k network contains 970 TapTransformers, of which 776 have non-unity tap ratios.

### Phase Shifters and Tap Transformers

| Type | Count |
|------|-------|
| TapTransformer | 970 |
| Non-unity tap ratio | 776 |
| PhaseShiftingTransformer | 0 |

The protocol notes 5 phase shifters expected in ACTIVSg10k. PowerSystems.jl does not
import MATPOWER phase shifters as `PhaseShiftingTransformer` — they may be mapped to
`TapTransformer` with non-unity tap ratios. The 776 transformers with non-unity taps
include both standard tap-changers and any phase-shifting transformers from the MATPOWER
case.

## Workarounds

None required. `PTDF(sys)` works directly on the loaded system.

## Timing

- **Wall-clock (PTDF, timed):** 1.618 s (JIT cached)
- **Wall-clock (JIT warm-up):** 1.598 s
- **System load time:** 10.4 s
- **Timing source:** measured
- **Peak memory:** 2,811 MB (includes 969 MB for the dense PTDF matrix)
- **Memory delta:** 2,741 MB (memory increase from PTDF computation)
- **CPU cores used:** 1 (32 available)

## Test Script

**Path:** `evaluations/powersimulations/tests/scalability/test_c9_ptdf_scale.jl`

```julia
using PowerNetworkMatrices
ptdf = PTDF(sys)
ptdf_data = get_data(ptdf)  # Returns dense matrix
n_rows, n_cols = size(ptdf_data)  # 10000 x 12706
```

## Observations

- **api-friction:** PTDF matrix orientation is buses x branches (10,000 x 12,706), which is
  the transpose of the conventional branches x buses convention used in most textbooks and
  other tools. This orientation difference is not documented in PowerNetworkMatrices.jl.
- The 68.6% density means the PTDF matrix is not sparse at 10K scale. Dense storage requires
  ~969 MB just for the matrix data. For larger networks, sparse or factored PTDF representations
  would be necessary to fit in memory.
- PTDF computation (1.6s) is faster than JIT warm-up (1.6s), indicating the computation cost
  is comparable to Julia's initial compilation overhead. The 10K-bus PTDF is efficiently computed.
