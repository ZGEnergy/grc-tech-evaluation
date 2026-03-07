# Observation: Architecture Quality -- B-3 Contingency Loop

**Tag:** arch-quality
**Test:** B-3 (Contingency Loop)
**Dimension:** extensibility

## Observation

The in-place branch toggling pattern (`set_available!(branch, false)` / `true`) is
exceptionally clean for contingency analysis. Key strengths:

1. No file reload between contingencies -- 46 DCPF solves in 82ms total.
2. Per-contingency solve time (post-JIT) is sub-millisecond (~0.07ms to ~1.5ms).
3. The `set_available!` API is part of the public PowerSystems.jl interface.
4. No deep copy or model reconstruction needed -- toggle and restore.

The 10 diverged contingencies (out of 46) are correctly identified as islanding
events where removing radial branches disconnects generator buses. PowerFlows.jl
handles these gracefully (returns nothing) rather than crashing.

## Impact

This is a production-ready pattern for N-1 security analysis. The combination of
in-place modification, sub-millisecond solve times, and clean failure handling makes
PowerFlows.jl well-suited for contingency screening applications.
