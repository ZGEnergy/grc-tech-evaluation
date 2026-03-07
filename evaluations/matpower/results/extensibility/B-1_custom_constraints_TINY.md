---
test_id: B-1
tool: matpower
dimension: extensibility
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 0.2434
peak_memory_mb: null
loc: 95
timestamp: "2026-03-06T13:00:00Z"
---

# B-1: Custom Constraints (Flow Gate Limit + Dual Values) on TINY (IEEE 39-bus)

## Result: PASS

## Approach

Used MATPOWER's built-in `toggle_iflims` extension, which implements interface flow
limits as a `userfcn` callback chain. This is the canonical way to add aggregate
flow constraints to DC OPF in MATPOWER.

**Steps:**
1. Define `mpc.if.map` (interface-to-branch mapping with direction signs)
2. Define `mpc.if.lims` (interface lower/upper flow limits in MW)
3. Call `toggle_iflims(mpc, 'on')` to register callbacks
4. Run `rundcopf(mpc, mpopt)` -- constraints are injected automatically
5. Read duals from `results.if.mu.u` and `results.if.mu.l`

No workaround needed. The interface flow limit is a first-class extension with
structured input/output.

## Test Configuration

- **Interface 1** (binding): branches 4 (2->25), 10 (5->6), 17 (9->39)
  - Threshold set to 80% of baseline aggregate flow (421.09 MW)
- **Interface 2** (non-binding): branches 1 (1->2), 2 (1->39)
  - Threshold set to 9999 MW (always slack)

## Results

| Interface | Flow (MW) | Lower Limit | Upper Limit | mu_lower | mu_upper | Binding? |
|-----------|-----------|-------------|-------------|----------|----------|----------|
| 1         | -421.09   | -421.09     | 421.09      | 6.3700   | 0.0000   | YES      |
| 2         | -97.60    | -9999.00    | 9999.00     | 0.0000   | 0.0000   | NO       |

- **Baseline objective:** 41263.94 $/hr (no constraints)
- **Constrained objective:** 41656.09 $/hr (+0.95%)
- **Baseline LMP range:** [13.5169, 13.5169] $/MWh (uniform -- no congestion)
- **Constrained LMP range:** [10.2749, 18.3240] $/MWh (spread: 8.05 $/MWh)

The flow gate successfully created locational price differentiation. The binding
constraint dual (6.37 $/MW) represents the marginal cost of relaxing the interface
limit by 1 MW.

## Binding Constraint Report

- Total interfaces: 2
- Binding interfaces: 1
- Interface 1: BINDING at lower limit (-421.09 MW), dual = 6.37 $/MW
- Interface 2: not binding (flow = -97.60 MW, within [-9999, 9999])

## API Friction Analysis

**Very low friction.** The `toggle_iflims` extension provides:
- Structured input format (`mpc.if.map`, `mpc.if.lims`) -- no raw matrix manipulation
- Automatic PTDF-based constraint formulation
- Structured output (`results.if.P`, `results.if.mu.l`, `results.if.mu.u`)
- Clean enable/disable toggle

The only non-obvious aspect is the `map` format: each row is `[interface_id, signed_branch_index]`
where negative sign indicates opposite flow direction. This is documented in the
`toggle_iflims` help text.

For custom constraints beyond interface flows, MATPOWER provides two additional paths:
1. **Direct A/l/u matrices:** `opf(mpc, A, l, u, mpopt)` for arbitrary linear constraints
   on optimization variables (requires understanding the variable ordering)
2. **userfcn formulation callback:** Register a function that receives the `opt_model`
   object and calls `om.add_lin_constraint()` or `om.add_nln_constraint()`

## Observations

- **arch-quality:** The `toggle_iflims` extension is a well-designed pattern --
  structured input, automatic constraint formulation, structured dual output.
  It serves as a template for other extensions (`toggle_reserves`, `toggle_softlims`).
- **api-friction:** Near-zero for interface flow limits specifically. The general
  A/l/u approach requires more expertise (variable ordering, per-unit scaling).

## Test Script

`evaluations/matpower/tests/extensibility/test_b1_custom_constraints_tiny.m`
