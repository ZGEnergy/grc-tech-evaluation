---
tool: matpower
dimension: expressiveness
network: TINY
tests: [A-1, A-2, A-3, A-4, A-5, A-7, A-8, A-9, A-10, A-11]
timestamp: "2026-03-06T00:00:00Z"
---

# Observations: MATPOWER Expressiveness (TINY)

## api-friction

**Low friction for core analyses (A-1 through A-4, A-7).** MATPOWER provides single-function
entry points for each analysis type (`rundcpf`, `runpf`, `rundcopf`). Load data with
`loadcase()`, configure options with `mpoption()`, call the solver, read results from the
returned struct. Three-step pattern for every analysis.

**Column-index ergonomics are the main friction point.** Results are stored in numeric
matrices (e.g., `results.bus`, `results.branch`) where columns are identified by integer
index. The `define_constants` script loads named constants (`PF`, `LAM_P`, `MU_SF`, etc.)
that map to column numbers. Without `define_constants`, users must memorize or look up
column indices, and the branch result matrix is particularly confusing: columns 14-17 are
PF/QF/PT/QT (flows), while 18-19 are MU_SF/MU_ST (shadow prices). This is documented but
error-prone.

**A-4 (AC feasibility):** Straightforward -- modify `gen(:, [PG PMIN PMAX])` to fix
dispatch, then call `runpf()`. No special API needed. Violations are directly readable
from `bus(:, VM)` and branch apparent power vs `RATE_A`.

**A-7 (contingency sweep):** Low friction. Toggle `branch(bi, BR_STATUS) = 0` to trip a
branch, call `rundcpf()`, read results. No model reconstruction per contingency. However,
there is no built-in BFS/graph utility -- the adjacency list must be constructed manually
from `branch(:, [F_BUS T_BUS])`, requiring ~20 lines of boilerplate.

**A-8 (MOST stochastic): High friction.** MOST requires understanding five interrelated
data structures: `mpc` (base case), `xGenData` (reserve offers with 12 column types),
`transmat` (scenario probability tree), profiles (struct with `type`/`table`/`rows`/
`col`/`chgtype`/`values` fields), and `loadmd()` assembly. The profile `values` array
has a specific 3D structure `[nt x nj x n_elements]` that is not intuitive. The constants
from `idx_ct` (CT_TLOAD, CT_LOAD_ALL_PQ, CT_REL, etc.) must be loaded separately from
`define_constants`. Setting up MOST for case39 required ~180 lines of code and studying
multiple MOST test files. The data prep effort dwarfs the actual solve call.

**A-5 (MOST SCUC): High friction.** Requires the same MOST data structures as A-8, plus
understanding UC-specific xGenData columns (`CommitKey`, `CommitSched`, `MinUp`, `MinDown`).
Additionally, GLPK (the only MILP solver on Octave) cannot handle quadratic costs, requiring
conversion to piecewise-linear. Total setup is ~220 lines. The actual solve call is the
same one line: `mdo = most(mdi, mpopt)`.

**A-9 (MOST SCOPF): Moderate friction.** The contingency table format (`contab`) is
straightforward -- a numeric matrix with columns for label, probability, table type,
row, column, change type, and new value. Setting `most.security_constraints = 1` enables
SCOPF. However, bridge branch detection (to avoid infeasible contingencies) requires ~40
lines of graph analysis that MOST does not provide natively.

**A-10 (LMP decomposition): Low friction for lossless.** Extracting `LAM_P`, `MU_SF`,
`MU_ST` from results is trivial. Computing the PTDF matrix via `makePTDF()` is one call.
The decomposition `LMP = energy + congestion` is exact for lossless DC OPF. However,
adding a loss component requires building a custom formulation -- there is no option to
enable loss approximation in `rundcopf()`.

**A-11 (Distributed slack OPF): Very high friction.** No native support. The workaround
requires manually constructing the entire DC OPF problem using `opt_model` (~100 LOC):
`add_var`, `add_lin_constraint`, `add_quad_cost`, `solve`. Shadow price sign conventions
from `opt_model` differ from standard MATPOWER output, creating additional confusion.

## doc-gaps

**Core MATPOWER API:** Well-documented. The legacy API (`rundcpf`, `runpf`, `rundcopf`) has
good function help text and column indices are defined in `idx_bus`, `idx_brch`, `idx_gen`.

**MOST documentation is comprehensive but difficult to navigate.** The MOST manual (PDF) is
the primary reference but is dense. The profile system documentation is scattered across
`idx_profile.m`, `apply_profile.m`, and the manual. The built-in examples (`most/lib/t/`)
use 3-bus test cases that don't directly map to real-world setups. The most useful learning
path was reading `t_most_sp.m` (stochastic single-period) and `t_most_3b_3_1_0.m`
(multi-period), then adapting patterns to case39. No tutorial-style documentation exists
for "how to set up MOST for your own case."

**Lossy DC OPF: Undocumented absence.** The documentation does not clearly state that
`rundcopf()` is strictly lossless. The existence of `get_losses()` (which only works on AC
power flow results) creates confusion about whether losses are available in DC OPF.

**Distributed slack: Documented as absent.** GitHub issues #136, #63, #233 confirm distributed
slack is not implemented. The `makePTDF()` documentation mentions the weight vector argument
but does not explain how to use it for a distributed-slack OPF formulation.

**opt_model shadow price conventions:** The sign conventions for shadow prices returned by
`opt_model.get_soln('lin', {'mu_l', 'mu_u'}, ...)` differ from the standard MATPOWER
`results.bus(:, LAM_P)` output. This is not documented and requires experimentation.

## workaround-needed

**A-5 (SCUC): Stable workaround required.** GLPK cannot handle MIQP (quadratic costs with
integer variables). Converting polynomial costs to piecewise-linear approximation (~25 LOC)
is a well-known technique. With HiGHS available, this workaround would be unnecessary.

**A-8 required case augmentation (not a workaround).** case39 lacks ramp rates (all zero)
and has no wind generators, so these had to be added programmatically. This is expected --
MOST requires ramp rate data that standard MATPOWER cases may not include. The augmentation
is clean (append rows to `gen`/`gencost`, set `RAMP_10`/`RAMP_30`/`RAMP_AGC`).

**A-9 (SCOPF): No workaround needed.** MOST natively supports security-constrained
optimization via `contab` + `most.security_constraints = 1`. The bridge branch filtering
is additional user logic, not a workaround for missing functionality.

**A-10 (Lossy DC OPF): Loss component requires manual computation.** MATPOWER's DC OPF
is strictly lossless. The energy + congestion decomposition is exact and native. Adding
a loss component requires post-hoc computation from branch impedances and flows. This is
a stable workaround for the two-component case, but the loss component is not part of the
optimization.

**A-11 (Distributed slack): Stable workaround via opt_model.** Building a PTDF-based DC OPF
manually using `opt_model` is functional but requires ~100 LOC. The `makePTDF()` function
with weight vector provides the correct distributed-slack PTDF. The workaround correctly
produces different LMPs from single-slack OPF.

**No workarounds needed for A-4 or A-7.** Both used the standard public API directly.

## solver-issues

**A-1 through A-4:** No solver issues. DCPF (linear), ACPF (Newton-Raphson), and DCOPF
(MIPS QP) all converge immediately on case39.

**A-5 (MOST SCUC):** GLPK solved the 24-period MILP (3816 variables) in 1.67 seconds.
Post-solve pricing warning ("max relative mismatch = 3.17") indicates approximate shadow
prices, which is expected for MILP. No convergence issues.

**A-7 (contingency sweep):** Some N-1 contingencies produce singular B matrices when
branches to radial generator buses are removed. MATPOWER warns ("matrix singular to
machine precision") but handles gracefully -- `results.success = 0` allows clean
detection. This is correct behavior, not a solver bug.

**A-8 (MOST stochastic): MIPS struggles with large load uncertainty.** The built-in MIPS
solver failed to converge with +/-10% load variation combined with stochastic wind on the
39-bus system. Reducing to +/-3% load variation resolved the issue. The MOST manual
acknowledges that MIPS has limitations for larger stochastic problems and recommends
commercial solvers (Gurobi, CPLEX, MOSEK) for production use. With MIPS, the 12-period,
3-scenario problem (3252 QP variables) solved in ~1 second.

**A-9 (MOST SCOPF):** MIPS converged without issues on the 35-contingency SCOPF (2514
variables, 4455 constraints). No thermal relaxation was required. Solved in 1.26 seconds.

**A-10:** Standard DC OPF with tightened limits converged normally. MIPS handles the
constrained case without issues.

**A-11:** The manual `opt_model` QP converged via MIPS in 12 iterations.

**Note on A-3 LMP uniformity:** Despite case39 having nonzero RATE_A on all branches,
no flow limits bind at the DC OPF operating point, producing uniform LMPs (13.5169 $/MWh).
This is correct -- the network is not congested at this load level.
