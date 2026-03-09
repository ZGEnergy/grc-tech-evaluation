---
probe_id: probe-020
tool: powersimulations
source_test: C-3
probe_type: timing_verification
classification: claim_supported
reason: "C-3 reported wall_clock_seconds=null with estimated <60s; probe confirmed no actual timing was done — first run timed out at 600s (includes JIT), supporting the claim that timings were estimated, not measured"
solver_version: "HiGHS v1.21.1"
solver_version_match: true
timeout_seconds: 600
wall_clock_seconds: 600
timestamp: "2026-03-09T00:00:00Z"
---

# Probe 020: C-3 DCOPF Scale timing was estimated, not measured

## Original Claim

From `evaluations/powersimulations/results/scalability/C-3_dcopf_scale.md` (v4 eval):

> **wall_clock_seconds: null**
>
> "HiGHS is expected to solve the MEDIUM DCOPF in < 60s (QP with ~15k constraints)."

The claim under investigation is that four scalability tests (C-3, C-4, C-5, C-6) report
estimated timings without actual measurement. The C-3 result file has `wall_clock_seconds: null`
and uses language like "expected to solve" and "estimated" throughout.

## Probe Methodology

Wrote a Julia script that:
1. Loads the ACTIVSg 10k network via `System("/workspace/data/networks/case_ACTIVSg10k.m")`
2. Adds required time series boilerplate (SingleTimeSeries + transform)
3. Builds a `DecisionModel` with `PTDFPowerModel` and HiGHS solver
4. Attempts to solve 3 times, measuring wall-clock with `@elapsed`

Script: `sweep-data/v4-to-v5/probes/powersimulations/probe-020_script.jl`

Executed via:

```bash
.devcontainer/dc-exec -C /workspace/evaluations/powersimulations \
  timeout 600 julia --project=. <script_path>
```

## Probe Results

Raw output:

```
============================================================
Probe 020: DCOPF timing on ACTIVSg 10k
============================================================

--- Loading ACTIVSg 10k network ---
System load time: 11.5s
Buses: 10000
ThermalStandard: 1136
RenewableDispatch: 634
Lines: 9726, Transformer2W: 2010, TapTransformer: 970
Total generators: 2485

--- Fixing generator limits ---
Fixed 0 generators

--- Adding time series ---
Time series setup: 4.03s

--- Run 1 (includes JIT) ---
EXIT_CODE=124  (timeout)
```

The first build+solve attempt consumed >580s before being killed by the 600s timeout.
System load took ~11.5s and time series setup ~4s, leaving ~584s for the build+solve
which did not complete.

No stderr errors were produced -- the process was simply killed by `timeout`.

## Analysis

1. **The `wall_clock_seconds: null` is confirmed.** The C-3 result file explicitly sets
   this to null and uses estimated language ("expected to solve in <60s"). This is not
   a formatting oversight -- the test was never timed.

2. **The "<60s" estimate appears optimistic.** The probe's first run (with JIT compilation)
   exceeded 580s without completing. While JIT adds significant overhead for PSI's first
   invocation (the A-3 test on 39-bus took 48s for its first HiGHS solve including JIT),
   the 10k network's PTDF matrix (10000x12706) is vastly larger and the JIT overhead
   alone cannot explain a >10x gap.

3. **Caveats:** This probe only attempted the first (JIT-inclusive) run. Subsequent warm
   runs would likely be significantly faster. The C-3 claim of "<60s" may refer to the
   solver-only time (excluding JIT and PTDF computation), which is plausible for the
   QP portion alone. However, the claim is presented without qualification in the result
   file.

4. **The core claim being probed -- that timings were estimated, not measured -- is
   unambiguously supported** by the `null` wall_clock_seconds and estimation language.

## Classification Rationale

Classified as **claim_supported** because:
- The C-3 result file explicitly uses `wall_clock_seconds: null`
- The language "expected to solve" and "estimated" confirms no measurement was done
- The probe's attempt to actually measure timing shows the task is non-trivial (>580s
  with JIT on this hardware), reinforcing that the "<60s" figure is an estimate
- The claim being verified is specifically that timings were estimated rather than measured,
  and this is confirmed by both the source text and the probe's execution experience
