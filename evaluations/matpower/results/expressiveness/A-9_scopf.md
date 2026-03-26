---
test_id: A-9
tool: matpower
dimension: expressiveness
network: TINY
protocol_version: "v11"
skill_version: "v2"
test_hash: "b4012049"
status: fail
workaround_class: blocking
blocked_by: null
wall_clock_seconds: null
timing_source: measured
peak_memory_mb: 1.7
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 297
solver: "MIPS / GLPK"
timestamp: 2026-03-24T00:00:00Z
---

# A-9: Solve DC OPF with N-1 contingency constraints embedded in optimization

## Result: FAIL

## Approach

MATPOWER has no native SCOPF function (`runSCOPF()` or equivalent). The v11 protocol requires Benders iteration (>=2 iterations) or explicit feasibility confirmation. Three approaches were attempted:

### Approach 1: Benders-style iterative SCOPF (GLPK, linear costs)

1. Solved base-case DC OPF with GLPK (linear costs required since GLPK handles LP only).
2. Screened all 41 non-radial contingencies using `makeLODF()` -- found 83 post-contingency flow violations.
3. Added violated constraints as user linear constraints via `mpc.A/l/u`.
4. **Benders iteration 1:** Baseline cost $126,125.36, 83 new violations detected, 83 constraints added.
5. **Benders iteration 2:** Problem INFEASIBLE with 83 constraints.

The 70%-derated case39 network is N-1 infeasible: the available generation and transmission capacity cannot simultaneously satisfy load and all post-contingency flow limits. The worst post-contingency overload is 403.1% (branch 6->11 under outage of branch 33, LODF = 1.75), indicating severe rerouting requirements that exceed physical capacity.

### Approach 2: Full N-1 constraint set (MIPS, quadratic costs)

Built 646 LODF-based post-contingency flow constraints and injected via `mpc.A/l/u`. MIPS solver encounters numerical singularity (rcond ~4e-17) and fails to converge. This is a [mixed: MIPS cannot handle the augmented constraint matrix numerically; a commercial solver might succeed but the problem itself is infeasible].

### Approach 3: MOST contingency framework (not pursued)

MOST supports contingency states with probability weighting but requires substantial setup boilerplate (mdi struct construction). Not pursued after the Benders approach demonstrated network-level N-1 infeasibility.

## Output

| Metric | Value |
|--------|-------|
| Baseline DC OPF cost (A-3) | $219,748.32 |
| N-1 contingencies screened | 41 (5 radial excluded) |
| Post-contingency violations | 83 |
| Worst post-contingency overload | 403.1% |
| Benders iterations completed | 2 (infeasible at iter 2) |
| SCOPF solve | Failed (N-1 infeasible + MIPS numerical issues) |

### N-1 Contingency Screening

Using `makePTDF()` and `makeLODF()` (documented APIs), 83 post-contingency flow violations were identified in the base-case DC OPF dispatch. 5 radial branches were excluded (LODF contains Inf for island-creating outages). The worst violation is 403% overload on branch 6->11 under outage of branch 33.

### Root Cause Analysis

The failure has two contributing factors:

1. **Network-level infeasibility** [solver-specific / network configuration]: The 70%-derated case39 network is inherently N-1 infeasible. No SCOPF solver -- even a commercial one -- can find a feasible dispatch because the transmission capacity after derating is insufficient to reroute flows under worst-case contingencies.

2. **No turnkey SCOPF** [tool-specific]: MATPOWER requires manual LODF computation and user constraint injection. The `mpc.A/l/u` interface works for injecting linear constraints, but the user must build the contingency constraint matrix from scratch using `makePTDF()`, `makeLODF()`, and `makeBdc()`.

## Workarounds

- **What:** LODF-based N-1 constraint injection via `mpc.A/l/u` user constraint interface with Benders iteration
- **Why:** No native SCOPF function in MATPOWER
- **Durability:** blocking -- The workaround mechanism (user constraint injection) is a documented public API, but the underlying problem (70%-derated case39 N-1 infeasibility) prevents any solution. Even with a different solver, the SCOPF is infeasible on this network configuration.
- **Grade impact:** Fail. MATPOWER can formulate SCOPF constraints using documented APIs (`makePTDF`, `makeLODF`, `mpc.A/l/u`), and the Benders workflow completed 2 iterations before detecting infeasibility. The API building blocks exist, but there is no turnkey SCOPF function, and the MIPS solver has numerical limitations with large constraint sets.

## Timing

- **Wall-clock:** N/A (solve failed)
- **Timing source:** measured
- **Peak memory:** 1.7 MB
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/matpower/tests/expressiveness/test_a9_scopf.m`

Key API calls: `makePTDF()`, `makeLODF()`, `makeBdc()`, `rundcopf()` with `mpc.A/l/u` user constraints, Benders iteration loop.
