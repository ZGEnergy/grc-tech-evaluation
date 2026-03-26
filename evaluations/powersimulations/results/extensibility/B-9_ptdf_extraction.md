---
test_id: B-9
tool: powersimulations
dimension: extensibility
network: TINY
protocol_version: "v11"
skill_version: "v2"
test_hash: "3c9003ed"
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 0.001
timing_source: measured
peak_memory_mb: 856.6
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 220
solver: null
timestamp: "2026-03-24T00:00:00Z"
---

# B-9: PTDF Matrix Extraction and Verification

## Result: PASS

## Approach

Computed the PTDF matrix using `PowerNetworkMatrices.PTDF(sys)` and verified that
PTDF-predicted flows match DCPF-solved flows within the 1e-6 tolerance.

**PTDF extraction:** Single API call `ptdf = PTDF(sys)`. The matrix is stored in
`ptdf.data` (a dense `Matrix{Float64}`), with bus indices in `ptdf.axes[1]` and
branch names in `ptdf.axes[2]`.

**Flow prediction:** `predicted_flows = ptdf.data' * Pinj` where `Pinj` is the net
injection vector (P_gen - P_load per bus, in per-unit) ordered by the PTDF bus axis.

**Phase shifters:** IEEE 39-bus has no phase-shifting transformers (all SHIFT=0 in
MATPOWER branch data, no `PhaseShiftingTransformer` components in the System). No
Pbusinj/Pfinj corrections needed.

## Output

**PTDF matrix dimensions:** 39 buses x 46 branches.

**PTDF statistics:**

| Metric | Value |
|--------|-------|
| Min element | -1.000000 |
| Max element | 1.000000 |
| Mean |element| | 0.151451 |
| Non-zero fraction (>1e-10) | 60.76% |

**Flow comparison (46 branches):**

| Metric | Value |
|--------|-------|
| Max error | 1.155e-14 p.u. (1.155e-12 MW) |
| Mean error | 1.568e-15 p.u. (1.568e-13 MW) |
| Branches compared | 46 / 46 |

All 46 branches match to machine precision. The max error of 1.15e-14 p.u. is 8 orders
of magnitude below the 1e-6 tolerance. This confirms that PowerNetworkMatrices.jl's
PTDF computation and PowerFlows.jl's DCPF solve are mathematically consistent.

**LODF also available:** `LODF(sys)` returns a 46x46 Line Outage Distribution Factor
matrix in 0.016 s. Same one-line API pattern.

**Sample flow comparison (top 5 by error, all effectively zero):**

| Branch | PTDF Flow (p.u.) | DCPF Flow (p.u.) | Error (p.u.) |
|--------|------------------|-------------------|--------------|
| bus-1-bus-2-i_1 | -1.78353726 | -1.78353726 | 0.0 |
| bus-1-bus-39-i_2 | 0.80753726 | 0.80753726 | 0.0 |
| bus-2-bus-3-i_3 | 3.33430081 | 3.33430081 | 0.0 |
| bus-2-bus-25-i_4 | -2.61783807 | -2.61783807 | 0.0 |
| bus-2-bus-30-i_5 | -2.50000000 | -2.50000000 | 0.0 |

## Workarounds

None required. PTDF extraction is a first-class feature of PowerNetworkMatrices.jl.

## Timing

- **PTDF computation:** 0.0003 s (second run, after JIT warm-up)
- **DCPF solve:** 0.0008 s
- **LODF computation:** 0.016 s
- **Timing source:** measured
- **Peak memory:** 856.6 MB (Julia process RSS)

## Test Script

**Path:** `evaluations/powersimulations/tests/extensibility/test_b9_ptdf_extraction.jl`

Key API pattern:
```julia
using PowerNetworkMatrices

# 1 LOC: Extract PTDF
ptdf = PTDF(sys)

# Access matrix data
ptdf_matrix = ptdf.data          # 39 x 46 Matrix{Float64}
bus_axes = ptdf.axes[1]          # Vector{Int} of bus numbers
branch_axes = ptdf.axes[2]       # Vector{String} of branch names

# 1 LOC: Predict flows
predicted_flows = ptdf_matrix' * pinj

# LODF also available
lodf = LODF(sys)                 # 46 x 46 Matrix{Float64}
```

## Observations

- **arch-quality:** PowerNetworkMatrices.jl provides a clean, purpose-built API for
  network matrix computation. `PTDF(sys)` is a single constructor call that handles
  all internal complexity (admittance matrix construction, reference bus handling,
  KLU factorization).
- **arch-quality:** The matrix is stored as a standard Julia `Matrix{Float64}`, not
  wrapped in a custom type that would require special access patterns. This means
  standard linear algebra operations (transpose, matrix-vector multiply) work directly.
- The axes metadata (`ptdf.axes[1]` for buses, `ptdf.axes[2]` for branches) provides
  clean mapping between matrix indices and physical component names -- no manual index
  bookkeeping required.
- PowerNetworkMatrices.jl also offers `VirtualPTDF(sys)` for lazy/row-by-row computation
  on large networks (memory-efficient), and `VirtualLODF(sys)` for the same pattern
  with LODF.
- No phase-shifter corrections were needed for case39. For networks with phase-shifting
  transformers, PowerNetworkMatrices.jl handles them internally in the admittance matrix
  construction.
