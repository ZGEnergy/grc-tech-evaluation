---
tag: api-friction
dimension: expressiveness
test_id: A-6
observed: 2026-03-11
tool: powermodels
version: 0.21.5
---

# API Friction: `baseMVA` returned as `Int` rather than `Float64`

## Observation

`PowerModels.parse_file` returns `data["baseMVA"]` as `Int` (value `100`) when parsing MATPOWER `.m` files with integer baseMVA. This causes `MethodError` in functions with `::Float64` type annotations:

```

MethodError: no method matching set_period_loads!(..., ::Int64)
MethodError: no method matching add_ramp_constraints!(..., ::Int64)

```

## Fix

Change all function signatures from `base_mva::Float64` to `base_mva::Real`. This is the correct type annotation since `baseMVA` can be an integer or float depending on the input file.

## Frequency

Affects any function that:
1. Takes `base_mva` as a typed parameter with `::Float64`
2. Uses `base_mva` in arithmetic with generator cost coefficients

## Impact

Minor friction. The fix is one-line per function signature. Julia's type system makes this discoverable quickly (immediate `MethodError`). However, it adds an unexpected surprise for users coming from Python (where int/float arithmetic is seamless) or from typed languages that auto-promote integers to floats.
