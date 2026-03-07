# Observation: workaround-needed -- A-6 sced

**Test:** A-6 (SCED / Economic Dispatch)
**Dimension:** expressiveness
**Tool:** PowerModels.jl v0.21.5

## Finding

PowerModels has no built-in SCED (Security-Constrained Economic Dispatch) or any economic dispatch formulation. Like A-5 (SCUC), the entire SCED formulation must be user-assembled via JuMP. PowerModels contributes only MATPOWER file parsing.

The UC-ED two-stage decomposition requires:
1. Running the full UC MILP to obtain a commitment schedule
2. Extracting binary commitment values
3. Building a separate LP model with commitment fixed as parameters
4. Re-implementing all constraints (DC power flow, branch limits, ramp rates) in the ED model
5. Independently enforcing ramp rate constraints in the ED stage

This results in ~200 lines of manual JuMP code for a standard two-stage UC+ED workflow that other tools (e.g., UnitCommitment.jl from Argonne) handle with purpose-built APIs.

## Workaround Classification

**Stable.** The JuMP assembly approach is reliable and well-understood. The workaround will not break across PowerModels versions since it does not depend on internal APIs. However, the effort level is significant for a standard power systems workflow.

## Impact

High. SCED is a fundamental ISO market operation. A tool that requires ~200 lines of manual formulation code for UC+ED decomposition imposes significant development overhead compared to tools with built-in support.
