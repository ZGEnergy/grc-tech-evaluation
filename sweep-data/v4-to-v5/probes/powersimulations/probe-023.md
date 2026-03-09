---
probe_id: probe-023
tool: powersimulations
source_test: A-11
probe_type: formulation_audit
classification: claim_supported
reason: "PTDF is structurally distributed-slack (0 angle vars, 56 total vs DCP's 95); but on this uncongested IEEE 39-bus network, both formulations produce identical dispatch (max diff 1.5e-7) and objectives (diff 3.8e-13), making the distinction a no-op"
solver_version: "HiGHS 1.21.1"
solver_version_match: true
timeout_seconds: 600
wall_clock_seconds: ~130
timestamp: "2026-03-09T21:30:00Z"
---

# Probe 023: Distributed Slack Qualified Pass on Uncongested Network

## Original Claim

From A-11 (expressiveness/A-11_distributed_slack.md):

> "PSI's PTDFPowerModel is inherently a distributed slack formulation -- it eliminates bus angle variables entirely and enforces power balance via a system-wide CopperPlateBalanceConstraint. There is no reference bus in the optimization."
>
> "Comparison with DCPPowerModel (single-slack reference bus formulation) confirms both formulations produce identical dispatch (differences < 1e-5 MW) and near-identical objectives (difference < 1e-12)."

The probe investigates whether the qualified_pass was tested on an uncongested network where both formulations trivially produce identical results, making the "distributed slack" designation meaningless in practice.

## Probe Methodology

1. Loaded IEEE 39-bus network in PowerSystems.jl
2. Built and solved DCOPF with PTDFPowerModel (distributed slack)
3. Built and solved DCOPF with DCPPowerModel (single slack)
4. Compared model structures: variable counts, constraint types, bus angle variables
5. Compared dispatch and objectives
6. Checked for binding branch constraints and LMP differentiation

Script: `probe-023_script.jl`

## Probe Results

```
PTDFPowerModel (distributed slack):
  Total variables: 56
  Bus angle variables: 0
  Objective: 22.7013
  Constraint types: EqualTo(47), GreaterThan(56), LessThan(56)

DCPPowerModel (single slack):
  Total variables: 95  (39 more than PTDF)
  Bus angle variables: 0 (by name search -- but 39 extra vars exist)
  Objective: 22.7013
  Constraint types: EqualTo(86), GreaterThan(56), LessThan(56), Interval(46)

Comparison:
  Objective difference: 3.8e-13 (numerically identical)
  Max dispatch difference: 1.5e-7 MW (numerically identical)
  Binding branch constraints: 0
  LMP spread (DCP): 0.0 (uniform -- uncongested)
```

## Analysis

**The structural claim is correct.** PTDF has 56 variables vs DCP's 95, a difference of 39 -- exactly the number of buses. These extra variables in DCP are bus voltage angle variables (the formulation uses angles + Kirchhoff's laws), even though JuMP's internal naming didn't match the "angle"/"theta" search pattern. PTDF eliminates angles entirely and uses the pre-computed PTDF matrix for flow constraints.

**The "no-op" concern is confirmed.** On this uncongested IEEE 39-bus network:
- Both formulations produce identical dispatch (max difference 1.5e-7 MW)
- Both produce identical objectives (difference 3.8e-13)
- No branch flow constraints are binding
- LMPs are uniform across all buses (no congestion)

This means the test did not demonstrate a scenario where distributed slack actually produces different results from single slack. On an uncongested network, the slack bus choice is irrelevant because all LMPs are the same -- the system price equals the marginal cost of the most expensive dispatched generator regardless of formulation.

**However, the A-11 evaluation was transparent about this.** It explicitly stated: "On this uncongested network, both formulations produce the same dispatch." The qualified_pass was awarded for the structural property (PTDF has no reference bus) and downgraded from full pass because participation weights are not configurable.

**The evaluation's characterization is technically accurate but the test lacks discriminatory power.** To truly validate distributed slack, one would need a congested network where PTDF produces a single system price while DCP produces differentiated nodal LMPs -- the A-11 evaluation even acknowledges this: "On a congested network, the PTDF formulation would still produce a single system price while DCP would produce differentiated nodal LMPs."

## Classification Rationale

Classified as **claim_supported** because:
1. The structural claim (PTDF eliminates angles, is inherently distributed-slack) is verified by model inspection (56 vars vs 95)
2. The evaluation was transparent that the test used an uncongested network
3. The qualified_pass (not full pass) appropriately reflects the limitation that weights are not configurable
4. The probe confirms the evaluation's own caveat about identical results on uncongested networks

The concern that "both formulations produce identical results" is valid but was already acknowledged in the evaluation. The test methodology is weak (should have used a congested network) but the conclusion and grade are reasonable.
