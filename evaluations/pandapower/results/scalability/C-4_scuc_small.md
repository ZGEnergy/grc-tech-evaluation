---
test_id: C-4
tool: pandapower
dimension: scalability
network: SMALL
protocol_version: "v11"
skill_version: "v2"
test_hash: "7adff329"
status: fail
workaround_class: blocking
blocked_by: A-5
wall_clock_seconds: null
timing_source: estimated
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: null
solver: null
cpu_threads_used: null
cpu_threads_available: null
timestamp: "2026-03-24T00:00:00Z"
---

# C-4: SCUC 24hr on SMALL

## Result: FAIL

**Failure reason:** `unsupported_in_installed_version` | `cascaded-failure` from A-5

## Approach

C-4 requires solving a 24-hour Security-Constrained Unit Commitment (SCUC) on the ACTIVSg2000 network. This test depends on A-5 (SCUC on TINY), which failed because pandapower 3.4.0 does not support unit commitment.

pandapower is a steady-state network analysis tool. Its OPF functions (`rundcopp`, `runopp`) solve single-period continuous optimization only. The capabilities required for SCUC are absent [tool-specific]:

- No binary commitment variables
- No startup/shutdown cost modeling
- No minimum up/down time constraints
- No multi-period temporal coupling
- No ramp rate constraints

Since the prerequisite A-5 failed with `workaround_class: blocking`, C-4 cannot be attempted.

## Output

No output produced. Test was not executed.

## Workarounds

- **What:** No workaround exists within pandapower's API
- **Why:** SCUC is fundamentally outside pandapower's design scope
- **Durability:** blocking -- the feature would require building an entirely separate MILP formulation outside pandapower
- **Grade impact:** Cascaded failure from A-5; caps scalability grade for SCUC sub-question

## Timing

- **Wall-clock:** null (not executed)
- **Timing source:** estimated
- **Peak memory:** null
- **CPU cores used:** null

## Test Script

No test script produced. Blocked by prerequisite A-5.
