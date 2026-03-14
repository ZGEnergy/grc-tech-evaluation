---
test_id: A-10
tool: matpower
dimension: expressiveness
network: TINY
protocol_version: "v10"
skill_version: "v1"
test_hash: "dae00140"
status: fail
workaround_class: blocking
blocked_by: null
wall_clock_seconds: null
timing_source: measured
peak_memory_mb: 1.8
convergence_residual: null
convergence_iterations: null
loc: 350
solver: "MIPS"
timestamp: 2026-03-13T00:00:00Z
---

# A-10: Solve DC OPF with loss approximation. Decompose LMPs.

## Result: FAIL

## Approach

MATPOWER's DC OPF (`rundcopf`) is inherently lossless — the B-matrix formulation uses only branch reactance, not resistance. Two workarounds were attempted for loss-inclusive DC OPF:

### Step 1: Iterative loss injection (succeeded)

1. Solved standard DC OPF (lossless).
2. Computed branch losses as `loss_k = r_k * (Pf_k/baseMVA)^2 * baseMVA` (I^2*R losses).
3. Distributed losses to buses (half to each branch endpoint) as additional load.
4. Re-solved DC OPF with augmented loads.
5. Repeated until convergence (3 iterations, tolerance 0.1 MW).

This produced realistic loss estimates:
- Total losses: 44.07 MW (0.70% of load) -- within the 0.5-3% target range
- Lossy objective: $225,954.35 vs lossless $219,748.32 (2.8% increase)
- Converged in 3 iterations

### Step 2: LMP decomposition (failed)

Attempted to decompose LMPs into energy, congestion, and loss components using:
- **Energy:** LMP at the slack bus minus its congestion component
- **Congestion:** `-PTDF' * mu_net` where `mu_net = mu_sf - mu_st` (branch shadow prices)
- **Loss:** Residual = `LMP_total - LMP_energy - LMP_congestion`

**Result:** The loss component is identically zero at all 39 buses. This is because the iterative loss injection approach adds losses as additional load at buses, which the DC OPF treats as ordinary demand. The solver has no knowledge that these loads represent losses, so the LMP decomposition captures the full LMP as energy + congestion with zero residual.

A true marginal loss factor decomposition requires loss terms *inside* the optimization formulation (e.g., loss penalty factors multiplying generation/load injections), which MATPOWER's DC OPF does not support. MATPOWER's `get_losses()` function computes losses from AC PF results only.

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
| (a) Non-zero loss LMP components | FAIL | Loss component = 0 at all buses |
| (b) Total losses 0.5-3% | PASS | 0.70% |
| (c) Lossy obj > lossless obj | PASS | $225,954 > $219,748 |
| (d) LMP components sum to total | PASS | Max relative error = 0.0 |

### Per-Line Congestion Rent

| Branch | From-To | Flow (MW) | mu_sf | mu_st | Cong Rent ($/h) |
|--------|---------|-----------|-------|-------|-----------------|
| 3 | 2->3 | 350.00 | 379.48 | 0.00 | 132,818.75 |
| 20 | 10->32 | -630.00 | 0.00 | 229.03 | -144,286.22 |
| 27 | 16->19 | -420.00 | 0.00 | 193.43 | -81,239.72 |
| 37 | 22->35 | -630.00 | 0.00 | 225.75 | -142,222.20 |
| 46 | 29->38 | -840.00 | 0.00 | 114.24 | -95,964.03 |

## Workarounds

- **What:** Iterative loss injection (external to OPF) + manual PTDF-based LMP decomposition
- **Why:** MATPOWER DC OPF has no internal loss model and no LMP decomposition API
- **Durability:** blocking -- The iterative loss injection produces correct total losses and a higher objective, but cannot produce non-zero loss LMP components because the loss approximation is external to the optimization. A true lossy DC OPF with marginal loss factors would require modifying the power balance equations, which is not possible through MATPOWER's public API.
- **Grade impact:** Fail. Checks (b), (c), (d) pass but check (a) -- the defining feature of lossy DC OPF LMP decomposition -- fails.

## Timing

- **Wall-clock:** N/A (test failed on LMP decomposition)
- **Timing source:** measured
- **Peak memory:** 1.8 MB
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/matpower/tests/expressiveness/test_a10_lossy_dcopf_lmp.m`
