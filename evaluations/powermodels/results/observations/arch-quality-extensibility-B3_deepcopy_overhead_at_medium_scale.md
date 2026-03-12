# arch-quality: B-3 Contingency Loop — deepcopy overhead at MEDIUM scale

**Tag:** arch-quality
**Dimension:** extensibility
**Test:** B-3
**Network:** MEDIUM

## Observation

At MEDIUM scale (10k-bus, 12706 branches), `deepcopy(data_base)` takes **1.8–8.3s per contingency** (mean 4.76s, std is high due to GC pressure). Parsing from file takes 20.5s. The deepcopy/parse ratio is 0.232x — deepcopy is 4–5× faster than re-parsing.

However, the absolute deepcopy time is large. Running 46 contingencies costs ~219s just in `deepcopy` calls, out of a 266s total loop. This means **82% of contingency loop overhead is deepcopy overhead**, not DCPF solve time.

## Cause

Julia's `deepcopy` on a nested `Dict{String,Any}` structure must recursively copy all dict entries, which requires allocating thousands of small objects. At 10k-bus scale, the data dict contains:
- `data["bus"]` — 10000 entries
- `data["branch"]` — 12706 entries
- `data["gen"]` — 2485 entries
- `data["load"]`, `data["shunt"]`, etc.

Each entry is itself a `Dict{String,Any}` with ~15–25 fields. The total allocation is ~300k-500k small dict/array objects per deepcopy.

## Implication

For production N-1 screening at transmission scale, the `deepcopy` pattern becomes a bottleneck. At 12706 potential contingencies (full N-1), the deepcopy overhead would be ~16 hours. A more efficient approach would be:
1. **Sparse modification:** Only mutate `br_status` (one field), then restore it after the solve. This avoids deepcopy entirely but requires care to avoid modifying the solver's data structures.
2. **Pre-built formulation:** `instantiate_model` once, then rebuild only the affected constraint coefficient (not supported natively).
3. **PowerModelsSecurityConstrained.jl:** Purpose-built N-1 SCOPF that avoids per-contingency deepcopy.

## Rating

Medium severity. The `deepcopy` pattern passes the B-3 criterion (no re-parsing per iteration, deepcopy < parse time), but the absolute performance at MEDIUM scale is concerning for real-world N-1 screening workflows. Users building production contingency analysis tools should evaluate the sparse-modification alternative.
