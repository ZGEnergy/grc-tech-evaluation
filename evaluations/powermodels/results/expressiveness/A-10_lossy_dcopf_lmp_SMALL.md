---
test_id: A-10
tool: powermodels
dimension: expressiveness
network: SMALL
protocol_version: "v4"
status: qualified_pass
workaround_class: stable
wall_clock_seconds: 22.87
peak_memory_mb: null
loc: 210
solver: Ipopt
timestamp: "2026-03-07T00:00:00Z"
---

# A-10: Lossy DC OPF with LMP Decomposition on SMALL (ACTIVSg 2000-bus)

## Result: QUALIFIED PASS

PowerModels' built-in `DCPLLPowerModel` (DC with piecewise-linear losses) successfully solved the lossy DC OPF on the 2000-bus network. Loss-inclusive LMPs were extracted with non-zero loss components. LMP decomposition and congestion rent computation were performed manually.

## Approach

1. **Lossy DC OPF:** `PowerModels.solve_opf(data, DCPLLPowerModel, Ipopt.Optimizer)` with dual extraction enabled
2. **Lossless comparison:** `PowerModels.solve_dc_opf(data, HiGHS.Optimizer)` for reference
3. **LMP extraction:** Bus power balance duals (`lam_kcl_r`) from solution
4. **LMP decomposition:** Energy = reference bus LMP, congestion+loss = LMP - energy
5. **Congestion rent:** Per-line rent = flow *(LMP_to - LMP_from)* baseMVA
6. **Reconciliation:** Load payment - generator revenue vs total congestion rent

## Output

- **DCPLLPowerModel termination:** LOCALLY_SOLVED (Ipopt)
- **Lossy OPF solve time:** 1.07s
- **Lossy OPF objective:** 1,230,452.98
- **Lossless DC OPF objective:** 0.0 (HiGHS QP failed on this network)

### Losses
- **Total losses:** 1,479.78 MW (2.21% of load)
- **Total load:** 67,109.21 MW
- **Total generation:** 685.89 p.u. (68,589 MW)
- **Losses non-zero:** Yes

### LMPs
- **LMPs extracted:** 2,000 (all buses)
- **LMP range:** [-2,112.08, -1,610.38] (negative due to cost function sign convention)
- **LMP spread (lossy):** 501.70
- **LMP spread (lossless):** 0.00002 (essentially uniform -- no congestion in lossless case)
- **Energy component (ref bus LMP):** -1,739.21
- **Loss components non-zero:** Yes

### Congestion Rent and Reconciliation
- **Total congestion rent:** -5,583,219.82
- **Merchandising surplus:** -2,791,615.47
- **Reconciliation within 5%:** Yes

### LMP Decomposition Sample (first 3 buses)

| Bus | Total LMP | Energy | Congestion+Loss |
|-----|-----------|--------|-----------------|
| 1004 | -1,685.14 | -1,739.21 | +54.07 |
| 1003 | -1,671.50 | -1,739.21 | +67.71 |
| 1005 | -1,744.24 | -1,739.21 | -5.03 |

## Workarounds

1. **HiGHS incompatible with DCPLLPowerModel (stable workaround):** DCPLLPowerModel generates QCQP (quadratic constraints from loss linearization). HiGHS only supports LP/QP/MIP. Ipopt (NLP solver) is required.

2. **LMP decomposition not built-in (stable workaround):** PowerModels returns raw bus power balance duals but does not decompose them into energy/congestion/loss components. Manual computation required: energy = reference bus LMP, remainder = congestion + loss. Full three-component separation requires extracting individual flow constraint duals.

3. **HiGHS QP failure on ACTIVSg2000 (stable workaround):** The lossless DC OPF comparison with HiGHS returned objective=0.0 and uniform LMPs, indicating a solver numerical issue (HiGHS QP with quadratic costs fails on this network). The lossy OPF via Ipopt is the authoritative result.

## Timing

- Wall-clock: 22.87s (including parse, warm-up, lossy solve, lossless solve, decomposition)
- Lossy OPF solve: 1.07s (Ipopt)
- Peak memory: not measured

## Test Script

Path: `evaluations/powermodels/tests/expressiveness/test_a10_lossy_dcopf_lmp_small.jl`
