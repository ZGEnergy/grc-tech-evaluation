---
test_id: D-4
tool: powersimulations
dimension: accessibility
network: TINY
protocol_version: "v4"
status: qualified_pass
workaround_class: null
wall_clock_seconds: null
peak_memory_mb: null
loc: null
solver: null
timestamp: "2026-03-07T04:30:00Z"
---

# D-4: Error Quality — Deliberate Error Diagnostics

## Result: QUALIFIED PASS

## Finding

Error diagnostic quality is mixed. Type-safety errors (invalid bus type, wrong argument
types) produce clear, actionable messages thanks to Julia's type system and PowerSystems'
validation layer. However, semantically invalid configurations (zero line rate causing
infeasibility) can silently produce results without any warning, which is concerning
for production use.

## Evidence

### (a) Infeasible OPF — Line limit set to 0

**Test:** Set a line's thermal rating to 0.0, then solve DCOPF.

**Result:** Model built and solved SUCCESSFULLY with no error or warning.

| Metric | Value |
|--------|-------|
| Build status | BUILT |
| Solve status | SUCCESSFULLY_FINALIZED |
| Objective value | 22.70 (identical to unconstrained) |

**Diagnostic quality: POOR.** The PTDF-based network model (`PTDFPowerModel`) does
not enforce line flow limits when `rate=0.0`. The zero rate is treated as "no limit"
rather than "zero capacity." A user setting rate=0 to model a line outage would get
silently incorrect results. No warning is issued about the zero rate.

This is a significant usability concern — the tool should either (a) warn about
zero-rated lines, (b) interpret rate=0 as no-flow, or (c) document the behavior.

### (b) Missing generator cost curve

**Test:** Set a generator's cost to `ThermalGenerationCost(CostCurve(LinearCurve(0.0)), nothing, nothing, nothing)` (zero variable cost), then solve DCOPF.

**Result:** Model built and solved SUCCESSFULLY.

| Metric | Value |
|--------|-------|
| Build status | BUILT |
| Solve status | SUCCESSFULLY_FINALIZED |
| Objective value | 22.70 |

**Diagnostic quality: ACCEPTABLE.** Zero cost is mathematically valid (the generator
simply has no marginal cost). The tool correctly accepts this. Setting a wrong cost
TYPE (e.g., `RenewableGenerationCost` on a `ThermalStandard`) would be caught by
Julia's type system at the setter call.

The test also showed that PSI's type system prevents assigning incompatible cost
types — `set_operation_cost!(thermal_gen, RenewableGenerationCost(...))` would fail
with a `MethodError`. This is good type-safety behavior.

### (c) Invalid bus type

**Test 1 — ISOLATED bus with connected branches:**

```
InfrastructureSystems.ConflictingInputsError(
  "Branch bus-6-bus-31-i_14 is set available and connected to isolated bus bus-31"
)
```

**Diagnostic quality: EXCELLENT.** The error message names the specific branch and
bus causing the conflict. Thrown during DCPF solve (not silently ignored).

**Test 2 — Invalid integer enum value:**

```
KeyError: key 999 not found
```

**Diagnostic quality: ADEQUATE.** The error prevents the invalid value but doesn't
explain what valid values are. A more helpful message would list valid enum members.

**Test 3 — Wrong type (string instead of enum):**

```
ArgumentError: enum=ACBusTypes does not have value=invalid
```

**Diagnostic quality: GOOD.** Clear message that names the expected enum type.
Julia's dispatch system provides natural type-safety here.

**Test 4 — ACPF with ISOLATED ref bus:**

Same `ConflictingInputsError` as Test 1 — consistent behavior across DCPF and ACPF.

## Summary Table

| Error scenario | Detected? | Message quality | Rating |
|---------------|-----------|----------------|--------|
| (a) Line rate=0 → infeasible | No | Silent success | Poor |
| (b) Zero cost curve | N/A (valid) | N/A | Acceptable |
| (c1) ISOLATED bus + branches | Yes | Specific branch+bus named | Excellent |
| (c2) Invalid enum integer | Yes | Generic KeyError | Adequate |
| (c3) Wrong argument type | Yes | Names expected type | Good |

## Implications

The tool relies heavily on Julia's type system for input validation, which catches
many classes of errors at compile time or setter call time. However, semantic validation
(physically unreasonable but type-valid configurations) is weak. The zero-rate line
case is particularly concerning because it produces silently wrong results rather than
an error or warning. For the accessibility criterion, this represents mixed quality:
strong type-safety but weak domain-specific validation.

## Test Scripts

- `evaluations/powersimulations/tests/accessibility/test_d4a_infeasible_opf.jl`
- `evaluations/powersimulations/tests/accessibility/test_d4b_missing_cost.jl`
- `evaluations/powersimulations/tests/accessibility/test_d4c_invalid_bus.jl`
