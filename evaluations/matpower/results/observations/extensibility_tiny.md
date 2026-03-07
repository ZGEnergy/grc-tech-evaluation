---
tool: matpower
dimension: extensibility
network: TINY
tests: [B-1, B-3, B-4, B-7, B-8, B-9]
timestamp: "2026-03-06T13:00:00Z"
---

# Observations: MATPOWER Extensibility (TINY)

## api-friction

**Low friction across most tests.** MATPOWER's mutable struct-based data model
allows direct modification of case data (branch status, generator dispatch, interface
limits) without any model rebuild or update step. Each test used standard public API
functions with no undocumented calls.

- **B-1 (custom constraints):** The `toggle_iflims` extension provides structured
  input (`mpc.if.map`, `mpc.if.lims`) and structured output (`results.if.P`,
  `results.if.mu.l`, `results.if.mu.u`). Near-zero friction for this specific use case.
  For arbitrary custom constraints, the `opf(mpc, A, l, u)` approach requires
  understanding the OPF variable ordering (Va, Vm, Pg, Qg), which adds moderate
  friction. The `userfcn` formulation callback is more flexible but requires
  implementing up to five callback stages.

- **B-3 (contingency loop):** One-line branch disable/enable via `BR_STATUS` column.
  No model rebuild between iterations. The simplest possible contingency loop pattern.

- **B-4 (stochastic wrapping):** Low friction for the scenario loop itself. MOST's
  profile system accepts timeseries as numeric arrays -- no file I/O needed. Only
  profile `values` arrays change between scenarios; the base `mpc`, `xgd`, and solver
  options are reused. The initial MOST setup (xGenData, profiles, transition matrices)
  has moderate friction due to the multi-dimensional data structures, but this is
  one-time cost shared with A-8.

- **B-7 (AC feasibility):** Single column assignment to transfer DC OPF dispatch to
  AC PF input. No format conversion needed because all analysis types share the same
  struct format.

- **B-8 (reference bus config):** Near-zero friction for single-slack configuration
  (two struct assignments). Moderate friction for distributed slack: `makePTDF` supports
  it natively, but the OPF formulation does not -- requires manual PTDF-based OPF
  reformulation.

- **B-9 (PTDF extraction):** Zero friction. Single call `makePTDF(mpc)` returns the
  full nbr x nb matrix. Supports single slack, distributed slack weights, and
  transfer-specific subsets via optional arguments.

## doc-gaps

**Minor gap for custom constraint dual extraction.** The `opf.m` help text documents
`results.mu.lin.l` and `results.mu.lin.u` for user-added linear constraint duals,
but the mapping between constraint indices and the A/l/u row ordering requires
careful reading. The `toggle_iflims` extension avoids this by providing named output
fields (`results.if.mu`).

**No gap for contingency analysis.** The in-place struct modification pattern is
obvious from the data model documentation. No contingency-specific documentation
needed.

**No gap for PTDF.** `help makePTDF` is comprehensive, documenting all calling
conventions including distributed slack and transfer-specific modes. The requirement
for internal bus ordering is documented but not enforced (case39 happens to use
consecutive numbering; for other cases `ext2int` would be needed).

**Minor gap for MOST wrapping pattern.** The MOST manual documents the native
stochastic mode (multiple scenarios per period) thoroughly, but using MOST in
deterministic mode (1 scenario) as a multi-period DCOPF wrapper is not explicitly
documented as a pattern. It works naturally but requires the user to figure out that
`transmat{t} = 1` represents a single deterministic scenario.

## workaround-needed

**B-8 (c) distributed slack in OPF: stable workaround.** MATPOWER's OPF uses the
B-theta DC formulation which requires a single angle reference. Distributed slack
is supported in `makePTDF(mpc, weights)` but not in `rundcopf`. To solve a
distributed-slack OPF, users must construct the LP/QP manually using the PTDF
matrix. This is a well-understood reformulation but adds significant implementation
effort compared to a native distributed-slack OPF flag.

**None for other tests.** B-1, B-3, B-4, B-7, B-9 all used native API calls.

## arch-quality

**Strong.** Key architectural strengths:

1. **Unified data structure.** The `mpc` struct is used across all analysis types
   (PF, OPF, CPF) and all formulations (AC, DC). This enables seamless workflow
   composition (DC OPF -> AC PF) without format conversion or adapter layers.

2. **Mutable structs for iteration.** The in-place modification pattern
   (`mpc.branch(k, BR_STATUS) = 0`) is trivial and requires no "update model"
   or "invalidate cache" step. This makes contingency loops, sensitivity studies,
   scenario sweeps, and parameter sweeps natural to implement.

3. **Extension callback architecture.** The `userfcn` five-stage callback system
   (ext2int, formulation, int2ext, printpf, savecase) provides clean separation of
   concerns. The built-in toggles (`toggle_iflims`, `toggle_reserves`,
   `toggle_softlims`, `toggle_dcline`) serve as well-documented templates. The
   MATPOWER 8 `mp.extension` class offers a more modern alternative with full OO
   element composition.

4. **Rich sensitivity toolkit.** `makePTDF` and `makeLODF` provide direct access to
   the DC sensitivity matrices with flexible slack handling. These enable post-solve
   analysis (flow prediction, contingency screening) without re-solving, and support
   both single and distributed slack formulations.

5. **MOST as a multi-period wrapper.** MOST serves double duty: native stochastic
   optimization (A-8) and deterministic multi-period DCOPF with inter-temporal
   constraints (B-4 wrapping pattern). The profile system, while complex to set up,
   enables programmatic timeseries injection without per-hour solve loops.

**Weaknesses:**

- No built-in N-1 contingency screening function despite `makeLODF` enabling it.
- No distributed-slack OPF formulation despite `makePTDF` supporting distributed
  slack weights. The B-theta and PTDF formulations are architecturally separate.
- MOST setup boilerplate is substantial (xGenData, profiles, transition matrices)
  even for simple deterministic multi-period problems.
