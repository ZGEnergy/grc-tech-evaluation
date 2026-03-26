---
test_id: A-10
tool: matpower
dimension: expressiveness
network: TINY
protocol_version: "v11"
skill_version: "v2"
test_hash: "dae00140"
status: fail
workaround_class: blocking
blocked_by: null
wall_clock_seconds: null
timing_source: measured
peak_memory_mb: 1.7
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 375
solver: "MIPS"
timestamp: 2026-03-24T00:00:00Z
---

# A-10: Solve DC OPF with loss approximation. Decompose LMPs into energy, congestion, loss.

## Result: FAIL

## Approach

MATPOWER's DC OPF (`rundcopf`) is inherently lossless -- the B-matrix formulation (`makeBdc`) uses only branch reactance, not resistance. Two approaches were attempted:

### Step 1: Iterative loss injection (succeeded partially)

1. Solved standard DC OPF (lossless) as reference.
2. Computed branch losses as `loss_k = r_k * (Pf_k/baseMVA)^2 * baseMVA` (I^2*R approximation).
3. Distributed losses to buses (half to each branch endpoint) as additional load.
4. Re-solved DC OPF with augmented loads.
5. Iterated until convergence (3 iterations, tolerance 0.1 MW).

This produced realistic aggregate loss estimates: 44.07 MW (0.70% of load), within the 0.5-3% target range. Lossy objective ($225,954.35) exceeds lossless ($219,748.32).

### Step 2: LMP decomposition (failed)

Decomposed LMPs using standard PTDF-based methodology:
- **Energy:** LMP at the slack bus minus its congestion component
- **Congestion:** `-PTDF' * mu_net` where `mu_net = mu_sf - mu_st` (branch shadow prices)
- **Loss:** Residual = `LMP_total - LMP_energy - LMP_congestion`

**Result:** The loss component is identically zero at all 39 buses (max |loss LMP| = 0.000000e+00). The iterative loss injection adds losses as additional load at buses, but the DC OPF solver has no knowledge that these loads represent losses. The LMP decomposition captures the full LMP as energy + congestion with zero residual.

A true marginal loss factor decomposition requires loss terms *inside* the optimization formulation (e.g., loss penalty factors multiplying generation/load injections in the power balance constraint), which MATPOWER's DC OPF does not support. MATPOWER's `get_losses()` function computes losses from AC PF results only; it does not provide marginal loss factors.

## Output

### Lossy DC OPF Results

| Metric | Value |
|--------|-------|
| Lossless objective | $219,748.32 |
| Lossy objective | $225,954.35 |
| Cost increase | $6,206.03 (2.82%) |
| Total losses | 44.07 MW (0.70%) |
| Convergence iterations | 3 |
| Loss convergence | Yes |

### Consistency Checks

| Check | Result | Detail |
|-------|--------|--------|
| (a) Non-zero loss LMP components | **FAIL** | Loss component = 0.000000e+00 at all 39 buses |
| (b) Total losses 0.5-3% | PASS | 0.70% |
| (c) Lossy obj > lossless obj | PASS | $225,954.35 > $219,748.32 |
| (d) LMP components sum to total within 1% | PASS | Max relative error = 0.000000e+00 |

### Per-Line Congestion Rent

| Branch | From-To | Flow (MW) | mu_sf ($/MWh) | mu_st ($/MWh) | Cong Rent ($/h) |
|--------|---------|-----------|-------|-------|-----------------|
| 3 | 2->3 | 350.00 | 379.48 | 0.00 | 132,818.75 |
| 20 | 10->32 | -630.00 | 0.00 | 229.03 | -144,286.22 |
| 27 | 16->19 | -420.00 | 0.00 | 193.43 | -81,239.72 |
| 37 | 22->35 | -630.00 | 0.00 | 225.75 | -142,222.20 |
| 46 | 29->38 | -840.00 | 0.00 | 114.24 | -95,964.03 |

Total congestion rent: $-330,893.43/h.

## Workarounds

- **What:** Iterative loss injection (external to OPF) + manual PTDF-based LMP decomposition
- **Why:** MATPOWER DC OPF has no internal loss model and no LMP decomposition API
- **Durability:** blocking -- The iterative loss injection produces correct total losses and a higher objective, but cannot produce non-zero loss LMP components because the loss approximation is external to the optimization. A true lossy DC OPF with marginal loss factors would require modifying the power balance equations inside the formulation, which is not possible through MATPOWER's public API. [tool-specific: DC OPF formulation excludes resistance from B-matrix construction]
- **Grade impact:** Fail. Checks (b), (c), (d) pass but check (a) -- the defining feature of lossy DC OPF LMP decomposition -- fails.

## Timing

- **Wall-clock:** N/A (test failed on LMP decomposition criterion)
- **Timing source:** measured
- **Peak memory:** 1.7 MB
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/matpower/tests/expressiveness/test_a10_lossy_dcopf_lmp.m`
