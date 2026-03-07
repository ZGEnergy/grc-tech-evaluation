---
test_id: P2-3
tool: powermodels
dimension: p2_readiness
network: TINY
protocol_version: "v4"
status: informational
workaround_class: null
timestamp: "2026-03-07T00:00:00Z"
---

# P2-3: Commitment Injection (SCUC -> DCOPF -> AC PF)

## Result: INFORMATIONAL

## Finding

The full SCUC-to-AC-PF pipeline is **feasible but requires care at the AC PF step**. Locking commitments (step 2) and solving DCOPF (step 3) are trivial one-liners. However, `compute_ac_pf` (Newton-Raphson) crashes with a `KeyError` when generators have `gen_status=0`, requiring the use of `solve_ac_pf` (Ipopt-based) instead. The SCUC itself (step 1) must be user-assembled in JuMP (~140 LOC, as demonstrated in A-5).

## Evidence

### Step-by-Step Workflow Assessment

#### Step 1: Run SCUC -- obtain commitment schedule
- Capability: YES, but not built-in
- Effort: HIGH (~140 lines of JuMP code, as demonstrated in A-5)
- PowerModels contributes only data parsing (`parse_file`) and `make_basic_network`
- The entire MILP formulation (binary commitment variables, min up/down, ramp rates, reserve) must be built manually
- Alternative: `UnitCommitment.jl` (ANL-CEEESA) provides a dedicated SCUC package but is separate from PowerModels

#### Step 2: Lock commitments -- set gen_status from schedule
- Capability: YES, trivial
- Effort: TRIVIAL (1 line per generator)
- API: `data["gen"][id]["gen_status"] = 0` for decommitted generators
- The data dict is mutable; no serialization or reimport needed

#### Step 3: Solve DCOPF with locked commitments
- Capability: YES, single function call
- Effort: TRIVIAL
- API: `PowerModels.solve_dc_opf(data, optimizer)`
- Decommitted generators (gen_status=0) are correctly excluded from the optimization
- Important: decommitted generators are **excluded from the solution dict** entirely (no pg=0 entry). Downstream code must check `haskey()` rather than assuming all gen IDs are present.

Test result (IEEE 39-bus, 80% load, Gen 8 decommitted):

```

DC OPF Status: OPTIMAL
Objective: 29,344.05
9 generators dispatched, Gen 8 excluded from solution

```

At full load with 2 generators off (Gen 4 + Gen 8), DCOPF returned INFEASIBLE -- the case39 network is tight on capacity. This is expected and correct behavior.

#### Step 4: AC PF feasibility check
- Capability: YES, with caveats
- Effort: LOW (but requires awareness of the `compute_ac_pf` bug)

Two AC PF approaches were tested:

| Approach | Function | Handles gen_status=0 | Result |
|----------|----------|---------------------|--------|
| `compute_ac_pf` (Newton-Raphson) | Built-in NR solver | **NO -- crashes with KeyError** | `KeyError: key 37 not found` (bus of decommitted gen) |
| `solve_ac_pf` (Ipopt) | Optimization-based PF | YES | LOCALLY_SOLVED |

The `compute_ac_pf` crash is a bug in PowerModels v0.21.5: the internal `PowerFlowData` structure does not properly handle buses that lose all generators when gen_status=0. The workaround is to use `solve_ac_pf` with Ipopt, which correctly formulates the problem excluding decommitted generators.

AC PF result (solve_ac_pf with Ipopt, Gen 8 off):

```

Status: LOCALLY_SOLVED
Dispatch comparison (DC vs AC):
  Gen 1: DC=5.6192, AC=5.6192, Qg=1.0261
  Gen 2: DC=5.6192, AC=5.9523, Qg=1.5149  (slack absorbs losses)
  Gen 3-7, 9-10: AC pg matches DC pg exactly
  Gen 8: DECOMMITTED (excluded from solution)
Slack gen (Gen 2) absorbs 0.333 p.u. losses

```

### API Friction Points

1. **No built-in SCUC**: The biggest friction. Requires ~140 lines of JuMP code or external package.
2. **compute_ac_pf bug with gen_status=0**: Must use `solve_ac_pf` (requires Ipopt) instead of the simpler `compute_ac_pf`. This is a non-obvious failure mode.
3. **Missing solution entries for decommitted gens**: Downstream code cannot assume all generator IDs exist in the solution dict. Must use `haskey()` checks.
4. **No pipeline orchestration**: Each step is independent; there is no built-in workflow that chains SCUC -> economic dispatch -> AC feasibility. The user orchestrates the pipeline manually.

### Effort Summary

| Step | Description | LOC | Effort Level |
|------|-------------|-----|-------------|
| 1 | SCUC (commitment schedule) | ~140 | HIGH (manual JuMP formulation) |
| 2 | Lock commitments | 1-2 | TRIVIAL |
| 3 | DCOPF with commitments | 3-5 | TRIVIAL |
| 4 | AC PF feasibility | 10-15 | LOW (must use solve_ac_pf, not compute_ac_pf) |
| Total | Full pipeline | ~160 | MODERATE-HIGH |

## Implications

- **Phase 2 readiness: MODERATE.** Steps 2-4 are straightforward and well-supported. The main barrier is Step 1 (SCUC), which requires significant custom JuMP code or adoption of `UnitCommitment.jl`.
- The `compute_ac_pf` bug with `gen_status=0` is a known limitation. Production code should use `solve_ac_pf` with Ipopt for the feasibility check, which adds Ipopt as a required dependency.
- The overall workflow is feasible but requires expert-level knowledge of PowerModels internals (knowing which PF function to use, understanding solution dict structure for decommitted gens).
- For ZGE's use case (SCUC -> SCED -> feasibility), the PowerModels contribution is primarily as a data layer and DCOPF solver. The UC formulation and pipeline orchestration are user responsibilities.
