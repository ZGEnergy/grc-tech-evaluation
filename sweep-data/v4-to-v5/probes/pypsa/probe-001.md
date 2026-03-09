---
probe_id: probe-001
tool: pypsa
source_test: A-2
probe_type: convergence_check
classification: claim_debunked
reason: "Solver reports converged=False with 0 iterations; 83% of buses remain at flat start; original claim of PASS is not supported"
solver_version: "pypsa 1.1.2"
solver_version_match: true
timeout_seconds: 300
wall_clock_seconds: 7.29
timestamp: 2026-03-09T00:00:00Z
---

# Probe 001: ACPF convergence on ACTIVSg10k

## Original Claim

From `evaluations/pypsa/results/expressiveness/A-2_acpf_MEDIUM.md` (v4 evaluation):

> PyPSA's `n.pf()` (Newton-Raphson AC power flow) runs on the 10,000-bus ACTIVSg10k network
> in ~15.7s. Despite a convergence warning ("Power flow did not converge for ['now']"),
> the test code reports `converged: true` because the flat-start iteration produces usable
> voltage magnitude and flow results.
>
> Result: PASS

The claim acknowledges a non-convergence warning but asserts the result is a PASS because
"usable" voltage and flow values are produced.

## Probe Methodology

Loaded the ACTIVSg10k network via `matpowercaseframes` + `import_from_pypower_ppc` (same
method used by the evaluation tests). Ran `n.pf()` and inspected:

1. The convergence status returned by PyPSA
2. The number of Newton-Raphson iterations performed
3. Voltage magnitudes across all buses
4. Line and transformer flows
5. How many buses/lines remain at flat-start defaults

Script: `sweep-data/v4-to-v5/probes/pypsa/probe-001_script.py`

Command:

```bash
.devcontainer/dc-exec -C /workspace/evaluations/pypsa timeout 300 uv run python \
  /workspace/.claude/worktrees/sweep/v4-to-v5/sweep-data/v4-to-v5/probes/pypsa/probe-001_script.py
```

## Probe Results

```
PyPSA version: 1.1.2

Buses: 10000, Lines: 9726, Transformers: 2980, Generators: 2485

=== CONVERGENCE STATUS ===
  n_iter: {'0': {'now': 0}}
  error: {'0': {'now': nan}}
  converged: {'0': {'now': False}}

=== WARNINGS (from PyPSA logger) ===
  WARNING: Power flow did not converge for ['now'].

=== VOLTAGE ANALYSIS ===
  V magnitude range: 0.9616 - 1.0814 pu
  V magnitude mean: 1.0042 pu
  Buses with V == 1.0 (flat start unchanged): 8274 / 10000 (83%)
  All voltages at flat start: False

=== LINE FLOW ANALYSIS ===
  Line p0 range: -984.8 - 1047.6 MW
  Lines with zero flow: 8870 / 9726 (91%)

=== TRANSFORMER FLOW ANALYSIS ===
  Transformer p0 range: -14692.4 - 13832.6 MW

=== POWER BALANCE CHECK ===
  Total generation: 152005.6 MW
  Total load: 150916.9 MW
  Line losses: 3935.5 MW
  Transformer losses: NaN

Total wall clock: 7.29s
```

## Analysis

The probe reveals several critical issues with the original PASS classification:

1. **Zero iterations performed.** The Newton-Raphson solver ran 0 iterations (`n_iter: 0`)
   and returned `converged: False`. This is not a "did not converge after many iterations"
   situation -- the solver never even started iterating, likely due to a singularity or
   initialization failure.

2. **83% of buses at flat start.** 8,274 out of 10,000 buses have voltage magnitude
   exactly equal to 1.0 pu (the flat-start initial guess). Only 1,726 buses (those in a
   connected sub-network with generators that have voltage setpoints) have non-trivial
   voltage values.

3. **91% of lines have zero flow.** 8,870 out of 9,726 lines show exactly zero power
   flow, indicating the solver did not compute flows for the vast majority of the network.

4. **The original claim that results are "usable" is misleading.** The voltage range
   (0.96-1.08 pu) and line flow range (-985 to 1048 MW) cited in the original result
   come from the small minority of components that are in the connected sub-network
   containing active generators. The network as a whole was not solved.

5. **The original result says "converged: true"** but the probe finds `converged: False`.
   The original evaluation may have had a bug in its convergence check logic.

6. **Transformer NaN losses** further indicate incomplete computation.

The original claim describes this as a PASS with "usable" results despite non-convergence.
The probe shows the solver performed zero iterations, left 83% of buses unsolved, and
explicitly reported non-convergence. Calling this a PASS misrepresents PyPSA's ability
to solve ACPF on this network.

## Classification Rationale

Classified as **claim_debunked** because:

- The original result says `converged: true` but the solver returns `converged: False`
- The original result says the solver "produces usable voltage magnitude and flow results"
  but 83% of buses are at flat start and 91% of lines have zero flow
- The solver performed 0 Newton-Raphson iterations, indicating it never attempted to solve
- A test that reports PASS when the solver explicitly says it did not converge, performed
  zero iterations, and left the vast majority of the network unsolved is not a valid PASS
