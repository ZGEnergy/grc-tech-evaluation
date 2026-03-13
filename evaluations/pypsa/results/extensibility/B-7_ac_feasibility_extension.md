---
test_id: B-7
tool: pypsa
dimension: extensibility
network: TINY
protocol_version: v9
skill_version: v1
test_hash: 7d05d8b8
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 332
solver: null
timestamp: 2026-03-11T00:00:00Z
---

# B-7: AC Feasibility Extension Assessment (ac_feasibility_extension)

## Result: PASS

## Approach

A-4 passed without requiring a workaround — PyPSA's in-memory architecture natively supports the DC OPF → AC feasibility check workflow without file export/reimport. B-7 assesses the extensibility implications: how easily a developer can build on or extend this workflow, whether the `pf()` return structure constitutes a programmatic extension concern, and the overall effort level.

The assessment is based on static code audit of `test_a4_ac_feasibility_tiny.py` (332 LOC) and cross-referencing with the B-6 architecture assessment. No additional test script was written — the A-4 test script is the definitive artifact.

## Output

### Workflow Decomposition

The DC OPF → AC feasibility check workflow decomposes into four well-defined steps, each with a clear PyPSA API call:

| Step | API | Extensibility |
|------|-----|--------------|
| 1. Load network | `pypsa.Network()` + `import_from_pypower_ppc()` | Clean; re-usable across tests |
| 2. Apply dispatch | `n.generators_t.p_set = DataFrame` | In-memory DataFrame assignment; trivially scriptable |
| 3. Run AC PF | `n.pf(snapshots=[...])` | Single call; accepts snapshot list for multi-period extension |
| 4. Extract results | `n.buses_t.v_mag_pu`, `n.lines_t.p0` | Zero-friction DataFrames; no unwrapping |

All four steps use documented public API. The workflow composes naturally — no hidden state dependencies or required teardown between steps.

### API Friction: pf() Return Structure

The one extensibility concern inherited from A-4 is the `pf()` return value. `n.pf()` returns a `pypsa.definitions.structures.Dict` with keys `n_iter`, `error`, `converged` (each a DataFrame), not a simple dict or named tuple. This structure is not described in the primary API documentation.

**Developer impact:** To parse convergence status programmatically, a developer must write:
```python
converged = bool(pf_result["converged"].values.flatten()[0])
n_iter    = int(pf_result["n_iter"].values.flatten()[0])
residual  = float(pf_result["error"].values.flatten()[0])
```
rather than the intuitively expected `pf_result.converged`. This is a discoverability problem but not a correctness problem — once understood, the pattern is stable and repeatable.

**Multi-period extension:** The DataFrame structure is actually advantageous for multi-snapshot use. With `n.pf(snapshots=n.snapshots)`, each DataFrame row corresponds to one snapshot, making batch convergence checking straightforward without any loop.

### Effort Assessment

| Concern | LOC in A-4 | Nature |
|---------|-----------|--------|
| Network loading | ~20 | Boilerplate; same across all tests |
| Dispatch application | ~15 | Trivial DataFrame assignment |
| AC PF invocation | 3 | Single call + timing |
| Convergence extraction | ~25 | Inflated by `pf()` return structure friction; would be ~5 LOC with a documented helper |
| Voltage violation check | ~30 | Straightforward pandas |
| Thermal violation check | ~40 | Straightforward pandas; repeated for lines + transformers |
| Reporting / output | ~100 | Test harness boilerplate |

The workflow core (steps 2–4 above) is approximately 75 substantive LOC once boilerplate is stripped. The convergence extraction block (~25 LOC) accounts for a disproportionate share relative to its functional role — a direct consequence of the undocumented `pf()` return structure.

### Hypothetical Workaround Durability

A-4 required no workaround. If it had (e.g., if setting `generators_t.p_set` had required reimport), the natural workaround — serializing to HDF5 via `n.export_to_hdf5()` and reimporting — would have been **stable** (documented public API). No fragile or blocking path would have been needed.

## Workarounds

None required. A-4 passed cleanly; no workaround was needed in the upstream test, and no extensibility workaround is needed to build on this workflow.

The `pf()` return structure friction is classified as API friction (not a workaround) because the documented public interface does work — it is merely underdocumented. See observation `api-friction-extensibility-B-7_ac_feasibility_extension.md`.

## Timing

- **Wall-clock:** not measured (code audit; no execution in B-7)
- **Timing source:** null
- **Peak memory:** not measured
- **Note:** A-4 wall-clock was 1.100 s; AC PF solve alone ~0.087 s

## Test Script

No separate test script for B-7. The workflow under assessment is implemented in:

**Path:** `evaluations/pypsa/tests/expressiveness/test_a4_ac_feasibility_tiny.py`

Key extensibility-relevant pattern — multi-snapshot extension requires only changing the snapshot argument:
```python
# Single snapshot (A-4 baseline)
pf_result = n.pf(snapshots=[snapshot])

# Multi-period extension (no structural change needed)
pf_result = n.pf(snapshots=n.snapshots)
# pf_result["converged"] → DataFrame with one row per snapshot
```
