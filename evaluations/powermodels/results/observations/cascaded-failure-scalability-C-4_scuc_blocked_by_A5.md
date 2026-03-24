---
tag: cascaded-failure
source_dimension: scalability
source_test: C-4
tool: powermodels
severity: high
timestamp: 2026-03-24T16:00:00Z
---

# Observation: C-4 SCUC Scale Blocked by A-5 (SCUC Unsupported)

## Finding

C-4 (SCUC 24hr on SMALL 2000-bus network) is a cascaded failure from A-5. PowerModels.jl v0.21.5 does not natively support SCUC -- it is a steady-state single-period network optimization library. Unit commitment (binary commitment variables, min up/down time, startup/shutdown costs, multi-period coupling) is entirely outside its scope. Under v11 protocol, A-5 is recorded as `status: fail` with `failure_reason: unsupported_in_installed_version`.

## Context

In the v10 evaluation, C-4 was scored as `qualified_pass` using a ~300 LOC user-assembled JuMP MILP that bypassed PowerModels entirely (using it only for `parse_file`). Under v11, A-5 is now `fail` (unsupported), which means C-4 cannot be attempted -- the prerequisite SCUC capability does not exist. Both 1-thread and max-thread results are N/A.

## Implications

This cascaded failure confirms that PowerModels.jl has no SCUC capability at any scale. The SCUC gap is architectural, not scale-dependent. Any MILP scalability assessment for PowerModels would require evaluating user-assembled JuMP code rather than the tool itself, which does not meet the v11 evaluation criteria. This finding is relevant to the synthesis phase for comparing MILP scalability across tools.
