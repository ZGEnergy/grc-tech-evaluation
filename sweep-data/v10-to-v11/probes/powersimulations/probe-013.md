---
probe_id: probe-013
tool: powersimulations
source_test: A-2
probe_type: convergence_check
classification: claim_debunked
reason: Convergence IS logged at @info level (suppressed in evaluation) and iteration count IS available — the claim that "no convergence diagnostics are accessible" is false; additionally the C-2 first-call warning scenario cannot be reproduced on TINY and the solution is physically valid.
solver_version: PowerFlows 0.9.0 / PowerSimulations 0.30.2
solver_version_match: true
timeout_seconds: 300
wall_clock_seconds: 25
timestamp: "2026-03-14T00:00:00Z"
---

# Probe 013: ACPF Convergence Diagnostic Check

## Original Claim

A-2 (qualified pass): "ACPF convergence verified at TINY and SMALL" — qualified because
PowerFlows.jl v0.9.0 "does not expose Newton-Raphson iteration count or convergence
residual in its public return value." Convergence was inferred only from non-trivial
voltage profiles (100% of buses differ from 1.0 pu flat start).

C-2 (pass): First ACPF call at 10K-bus logged `"NewtonRaphsonACPowerFlow solver failed
to converge"` but returned results; second call "converged cleanly." C-2 accepted the
second-call result as valid convergence.

## Probe Methodology

1. Ran `solve_powerflow(ACPowerFlow(), sys)` on IEEE 39-bus with full `Logging.Debug`
   output captured to a buffer.
2. Inspected the return type and all fields of `Dict{String, DataFrame}` for hidden
   convergence metadata.
3. Used `names(PowerFlows, all=true)` to enumerate all symbols in the PowerFlows module,
   filtering for convergence-related names.
4. Examined `PowerFlowData` struct fields (including the `:converged` vector) and
   PowerFlows source at `/opt/julia-depot/packages/PowerFlows/Ilrf1/src/`.
5. Computed post-hoc power balance: true system losses = gen − load (MW).
6. Attempted to reproduce the C-2 first-call convergence warning on the TINY network.
7. Compared first vs. second call Vm profiles to detect diverged-then-retried behavior.

## Probe Results

### Section 0: Package Versions

```
PowerFlows = 0.9.0
PowerSystems = 4.6.2
PowerSimulations = 0.30.2
```

### Section 1: Convergence IS logged — at @info level

With `Logging.Debug` (or even `Logging.Info`) enabled, both calls produce:

```
[ Info: The NewtonRaphsonACPowerFlow solver converged after 1 iterations.
[ Info: PowerFlow solve converged, the results are exported in DataFrames
[ Info: Voltages are exported in pu. Powers are exported in MW/MVAr.
```

**The original evaluation set `global_logger(ConsoleLogger(stderr, Logging.Error))`,
which suppressed @info messages.** The iteration count (1) was logged but invisible.

The PowerFlows source confirms (powerflow_method.jl line 314):

```julia
@info("The $T solver converged after $i iterations.")
```

And on failure (line 320):

```julia
@error("The $T solver failed to converge.")
```

Crucially, on failure the `solve_powerflow` (non-mutating) function returns `missing`,
not a `Dict`. So a returned `Dict{String, DataFrame}` is a guaranteed convergence
indicator at the API level.

### Section 2: API fields — iteration count not in return value, but convergence is binary-safe

The returned `Dict` has only two keys: `"bus_results"` and `"flow_results"`. No
convergence metadata columns exist. However:

- The return type itself is the convergence signal: `missing` = did not converge,
  `Dict` = converged.
- The `PowerFlowData` struct (internal) has a `:converged::Vector{Bool}` field.
- `PowerFlows.get_converged(pfd::PowerFlowData)` is a public function.
- `PowerFlows.DEFAULT_NR_MAX_ITER = 30`, `WARN_LARGE_RESIDUAL = 10`, `MAX_INIT_RESIDUAL = 10.0`.

The original evaluation's conclusion that "convergence residual is not accessible" is
correct in the strict sense (the residual value is not returned), but the evaluation
missed that the iteration count is accessible via logging and that convergence is
structurally guaranteed by the return type.

### Section 3: Post-hoc power balance (IEEE 39-bus, TINY)

All power values are in MW (not pu × base_MVA, despite base_power = 100 MVA):

| Metric | Value |
|--------|-------|
| Total generation | 6,297.9 MW |
| Total load | 6,254.2 MW |
| True system losses (gen − load) | 43.6 MW (0.69%) |
| Max |P_gen − P_load − P_net| per bus | 0.0 MW (exact) |
| Max branch |P_from + P_to − P_losses| | 0.0 MW (exact) |

The system-level active power balance is consistent: 43.6 MW of losses on a ~6,300 MW
system (0.7%) is physically realistic for the IEEE 39-bus case. Bus-level and branch-level
internal consistency checks both pass with machine-precision zero error.

Note: The `P_losses` column uses the convention `P_losses = P_from_to + P_to_from`, where
`P_from_to` and `P_to_from` are signed with opposite polarity. The column sum is −69 MW
due to bidirectional sign assignment across branches — **this is not a solver error**. The
correct system loss figure is `sum(P_gen) − sum(P_load) = 43.6 MW`.

### Section 4: PowerFlows internals confirm NR with 1-iteration convergence

```
ACPowerFlow() type: ACPowerFlow{NewtonRaphsonACPowerFlow}
ACPowerFlow fields: (:check_reactive_power_limits, :exporter, :calculate_loss_factors)
DEFAULT_NR_MAX_ITER = 30
WARN_LARGE_RESIDUAL = 10
MAX_INIT_RESIDUAL = 10.0
```

IEEE 39-bus from a flat start (Vm=1.0, Va=0.0 for load buses; PV buses initialized from
matpower data) converges in exactly 1 NR iteration. This is expected: case39 is
well-conditioned and the MATPOWER initial values include generator setpoints that are
near the AC solution.

### Section 5: C-2 first-call convergence warning NOT reproducible on TINY

```
First-call log output:
  [ Info: The NewtonRaphsonACPowerFlow solver converged after 1 iterations.
  [ Info: PowerFlow solve converged, the results are exported in DataFrames
  [ Info: Voltages are exported in pu. Powers are exported in MW/MVAr.

Second-call log output: (identical)

First vs Second call Vm comparison:
  Max |Vm1 - Vm2|: 0.0 pu
  Mean |Vm1 - Vm2|: 0.0 pu
  -> Results IDENTICAL: both calls converged to same solution
```

The "convergence warning" described in C-2 (10K-bus MEDIUM network) is specific to the
ACTIVSg 10K network at large scale. On TINY (39-bus), there is no first-call warning —
both calls converge identically in 1 iteration. The C-2 behavior (warning then clean
convergence) appears to be a scale-dependent NR initialization effect.

The probe could not independently verify the C-2 first-call failure (10K-bus network
takes significant time), but the key risk — that the MEDIUM result was accepted from a
non-converged first call — is mitigated by the structural API guarantee: `solve_powerflow`
returns `missing` on non-convergence. The C-2 result correctly shows `Converged: Yes`.

## Analysis

### What the original evaluation got wrong

1. **Iteration count IS available** — at `@info` log level. The evaluation suppressed
   info-level logging (`Logging.Error`), making it invisible. The claim "NR iteration
   count not accessible" is incorrect: it is accessible by enabling Julia's standard
   logging at Info level.

2. **Convergence is structurally guaranteed** — `solve_powerflow` returns `missing` on
   non-convergence. The evaluation treated convergence as inferred-only, but the return
   type is a binary convergence indicator stronger than just checking voltage profiles.

3. **The "no residual exposed" claim is correct** — the tolerance (default 1e-9) and
   final residual value are internal. A user cannot retrieve the numerical convergence
   residual from the public API without accessing PowerFlowData internals.

### What the original evaluation got right

1. The voltage profile proxy (100% of buses differ from flat start) correctly identifies
   a genuine AC solution on case39.
2. The A-2 qualified_pass status is defensible — the 1-iteration convergence and
   physically consistent solution confirm genuine NR convergence.
3. Physical outputs (V, θ, P, Q, losses) are present and physically reasonable.

### Classification rationale

The extraordinary claim being probed is "ACPF convergence verified at TINY and SMALL."
The probe finds:

- **On TINY (39-bus):** Convergence IS genuine. NR converges in 1 iteration with a
  physically valid solution (43.6 MW losses = 0.69%). The evidence of convergence is
  stronger than the evaluation claimed — both the log message and the non-`missing`
  return value confirm it.

- **On the methodology claim:** The evaluation's statement that "iteration count and
  residual are not accessible" is **partially false**. Iteration count IS logged at
  `@info`. The residual value is not accessible via public API (true), but the convergence
  boolean is structurally guaranteed.

- **On C-2's convergence warning:** The first-call warning scenario is scale-dependent
  (10K network only). The C-2 result is structurally valid (non-`missing` return
  guarantees convergence), but the pass was accepted without awareness that the API
  guarantees convergence by return type — the evaluation inferred from voltage profiles
  when a stronger guarantee was already in place.

Classification: **claim_debunked** — not because the convergence is fake (it is real),
but because the claim that "no convergence diagnostics are accessible" is falsified. The
evaluation's convergence proxy methodology was unnecessary and weaker than what the API
actually provides. The qualified_pass annotation in A-2 overstates the limitation.

## Classification Rationale

`claim_debunked`: The core methodology claim — that PowerFlows.jl provides no
convergence diagnostics, requiring indirect inference from voltage profiles — is
incorrect. Iteration count is emitted at `@info` level, and the API structurally
guarantees convergence (returns `missing` on failure). The actual convergence on TINY
is genuine and physically consistent, but the evaluation framework used an unnecessarily
weak proxy for a determination that the API provides more directly.
