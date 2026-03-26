---
test_id: A-5
tool: pandapower
dimension: expressiveness
network: TINY
protocol_version: "v11"
skill_version: "v2"
test_hash: "1640c770"
status: fail
workaround_class: blocking
blocked_by: null
wall_clock_seconds: 4.17
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 80
solver: null
timestamp: "2026-03-24T00:00:00Z"
---

# A-5: Solve 24-hour SCUC as MILP

## Result: FAIL

**Failure reason:** `unsupported_in_installed_version` [tool-specific]

## Approach

pandapower 3.4.0 was checked for SCUC capability. The tool is a steady-state network analysis package with no unit commitment formulation. Its OPF functions (`rundcopp`, `runopp`) solve single-period continuous optimization only.

The following capabilities required for SCUC are absent:

- **Binary commitment variables** -- pandapower's OPF is continuous; no integer/binary decision variables
- **Startup/shutdown cost modeling** -- no cost terms for generator state transitions
- **Minimum up/down time constraints** -- no temporal feasibility constraints
- **Multi-period temporal coupling** -- no inter-period linking; each `rundcopp()` call is independent
- **Ramp rate constraints** -- no inter-period dispatch rate limits

The PandaModels.jl Julia bridge (`pandamodels`) is not installed in the evaluation environment and would not resolve this gap -- PowerModels.jl itself does not natively support SCUC.

## Output

No SCUC solution was produced. The test confirmed the absence of the feature by introspecting the available API:

| OPF Function | Type | Multi-Period | Binary Variables |
|---|---|---|---|
| `pp.rundcopp()` | DC OPF | No | No |
| `pp.runopp()` | AC OPF | No | No |
| `pp.runpm_ac_opf()` | AC OPF (Julia) | No | No |
| `pp.runpm_dc_opf()` | DC OPF (Julia) | No | No |
| `pp.runpm_storage_opf()` | Storage OPF (Julia) | Partial | No |

## Workarounds

- **What:** No workaround exists within pandapower's API
- **Why:** SCUC is fundamentally outside pandapower's design scope -- it is a network analysis tool, not a market/scheduling tool
- **Durability:** blocking -- the feature would require building an entirely separate MILP formulation (e.g., via Pyomo or PuLP) that does not use pandapower's OPF at all
- **Grade impact:** Blocking failure on A-5 directly caps the expressiveness grade for this sub-question

## Timing

- **Wall-clock:** 4.17 s (import and capability check only -- no solve attempted)
- **Timing source:** measured
- **Peak memory:** not measured (no solve)

## Test Script

**Path:** `evaluations/pandapower/tests/expressiveness/test_a5_scuc.py`
