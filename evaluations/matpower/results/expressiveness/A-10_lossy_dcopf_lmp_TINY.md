---
test_id: A-10
tool: matpower
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: qualified_pass
workaround_class: stable
wall_clock_seconds: 0.237
peak_memory_mb: null
loc: 160
timestamp: "2026-03-06T00:00:00Z"
---

# A-10: Lossy DC OPF / LMP Decomposition on TINY (IEEE 39-bus)

## Result: QUALIFIED PASS

Qualified because MATPOWER has no native lossy DC OPF. LMP decomposition into
energy + congestion is exact for lossless DC OPF. The loss component requires
manual post-hoc computation and is NOT part of the optimization formulation.

## Details

- **Network file:** data/networks/case39.m (39 buses, 46 branches, 10 generators)
- **Solver:** MIPS (DC OPF)
- **Branch tightening:** 8 non-radial branches set to 95% of base-case flow
- **Binding constraints:** 5 branches
- **Converged:** Yes
- **Objective:** 42,225.63 $/hr (vs 41,263.94 unconstrained)
- **Wall clock:** 0.24 seconds

## LMP Decomposition (Lossless)

### Total LMPs

| Bus | LMP ($/MWh) |
|-----|-------------|
| Range | [9.87, 32.19] |
| Ref bus 31 | 12.40 |

### Energy Component
- **Method:** Reference bus LMP (uniform across all buses in lossless DC OPF)
- **Value:** 12.4044 $/MWh

### Congestion Component
- **Method:** Total LMP minus energy component
- **Range:** [-2.53, 19.79] $/MWh
- **Verification:** PTDF-based computation matches exactly (max error = 0.0)
- **Formula:** `congestion_i = sum_l(PTDF_l,i * mu_l)` where `mu_l = MU_SF - MU_ST`

### PTDF Verification
The congestion component was independently verified using the PTDF matrix:

```
congestion_from_PTDF = -H' * (MU_SF - MU_ST)
max |congestion_direct - congestion_PTDF| = 0.00000000
```

This confirms internal consistency of the lossless DC OPF formulation.

## Per-Line Congestion Rent

| Branch | From | To | Flow (MW) | RATE_A | MU_SF | MU_ST | Cong Rent ($/hr) |
|--------|------|----|-----------|--------|-------|-------|-----------------|
| 3      | 2    | 3  | 428.3     | 428.3  | 21.96 | 0.00  | 9,405.36        |
| 10     | 5    | 6  | -485.4    | 485.4  | 0.00  | 23.11 | 11,219.67       |
| 13     | 6    | 11 | -363.4    | 363.4  | 0.00  | 5.79  | 2,105.11        |
| 27     | 16   | 19 | -456.0    | 456.0  | 0.00  | 9.35  | 4,264.45        |
| 35     | 21   | 22 | -595.0    | 595.0  | 0.00  | 14.92 | 8,879.30        |

**Total congestion rent:** 35,873.89 $/hr

## Loss Approximation (Post-hoc)

Losses are not part of the DC OPF optimization. They were computed post-hoc:

- **Method:** `P_loss_l = R_l * (f_l / baseMVA)^2 * baseMVA` per branch
- **Total estimated losses:** 49.01 MW (0.78% of load)
- **Loss LMP range:** [-0.002, 0.008] $/MWh (negligible)

The loss LMP component is small because it is a second-order effect in the DC
approximation. These values are informational only -- they are NOT part of the
optimization and do NOT affect dispatch or pricing.

## LMP Reconciliation

| Check | Result |
|-------|--------|
| Total = Energy + Congestion | max error = 0.0 (exact) |
| PTDF congestion = direct congestion | max error = 0.0 (exact) |

The reconciliation is exact because the lossless DC OPF has a clean two-component
decomposition. A three-component decomposition (energy + congestion + loss) would
require a lossy formulation, which MATPOWER does not natively provide.

## Native Lossy DC OPF: NOT AVAILABLE

Key findings:
1. `rundcopf()` is strictly lossless -- no option to enable loss approximation
2. No `opf.dc.loss` or similar option exists in `mpoption()`
3. MOST supports some loss modeling in its DC network model, but this is not
   accessible via the standard single-period OPF API
4. The `get_losses()` function computes losses from an AC power flow solution,
   not from the DC OPF formulation
5. The building blocks exist (`makePTDF`, branch impedances) to construct a
   lossy DC OPF manually via `opt_model`, but this requires significant effort

## API Observations

### LMP Extraction (Low Friction)
- `results.bus(:, LAM_P)` gives total LMPs directly
- `results.branch(:, MU_SF)` and `MU_ST` give flow shadow prices
- `makePTDF(mpc)` provides the PTDF matrix for decomposition
- `define_constants` provides named column indices

### Loss Limitation (doc-gaps)
The MATPOWER documentation does not clearly state that `rundcopf()` is lossless.
Users must infer this from the mathematical formulation. The `get_losses()` function
exists but only works on AC power flow results, creating confusion about whether
losses are available in DC OPF.

## Test Script

`evaluations/matpower/tests/expressiveness/test_a10_lossy_dcopf_lmp_tiny.m`
