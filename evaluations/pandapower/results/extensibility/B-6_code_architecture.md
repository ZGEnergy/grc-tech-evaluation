---
test_id: B-6
tool: pandapower
dimension: extensibility
network: TINY
protocol_version: v11
skill_version: v2
test_hash: "eed84b8f"
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 0.69
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 251
solver: null
timestamp: "2026-03-13T00:00:00Z"
---

# B-6: Qualitative assessment of DCPF solve path architecture

## Result: PASS

## Approach

Traced the DCPF solve path through pandapower source code via runtime introspection (`inspect.getfile()`, `inspect.getsource()`). Documented the abstraction layers, separation of concerns, and documentation status of internal interfaces.

## Output

### Abstraction Layers (6 layers)

| Layer | Module | Function | Documented |
|-------|--------|----------|-----------|
| 1. Public API | `pandapower.run` | `rundcpp()` | Yes |
| 2. Internal Orchestration | `pandapower.powerflow` | `_powerflow()` | No |
| 3. Data Model Conversion | `pandapower.pd2ppc` | `_pd2ppc()` | No |
| 4. Problem Formulation | `pandapower.pypower.makeBdc` | `makeBdc()` | Yes |
| 5. Solver | `pandapower.pypower.dcpf` | `dcpf()` | Yes |
| 6. Result Extraction | `pandapower.results` | `_extract_results()` | No |

### Layer Details

1. **Public API (`rundcpp`):** Top-level user-facing function. Sets DC-specific options (transformer model, loading calculation, connectivity checking), then delegates to `_powerflow()`. Parameters are well-documented with docstrings and ReadTheDocs pages.

2. **Internal Orchestration (`_powerflow`):** Central pipeline coordinator. Calls (1) `_add_auxiliary_elements` to create dcline endpoint generators, (2) `_pd2ppc` for DataFrame-to-PYPOWER conversion, (3) `_run_pf_algorithm` to dispatch to the solver, (4) `_ppci_to_net` to map results back. This is the key separation point between the data model and the mathematical core.

3. **Data Model Conversion (`_pd2ppc`):** Converts pandapower's DataFrame-based network to PYPOWER's numpy-array format. Handles bus type assignment, generator aggregation, load injection conversion, branch impedance calculation, transformer modeling, switch handling, and bus reindexing. Returns both `ppc` (external numbering) and `ppci` (internal consecutive numbering). Stores lookup tables in `net._pd2ppc_lookups`.

4. **Problem Formulation (`makeBdc`):** Constructs DC power flow B-matrices from PYPOWER bus/branch arrays. Returns `Bbus` (bus admittance), `Bf` (branch-from admittance), `Pbusinj` and `Pfinj` (phase-shifter injection corrections). Uses the full B-matrix formulation incorporating tap ratios and phase shift angles.

5. **Solver (`dcpf`):** Direct linear solve: `Va = Bbus \ Pinj` using `scipy.sparse.linalg.spsolve`. Only 46 lines. No iterative solver needed for DC power flow.

6. **Result Extraction (`_extract_results`):** Maps PYPOWER result arrays back to pandapower DataFrames (`net.res_bus`, `net.res_line`, etc.) using the `_pd2ppc_lookups` stored during conversion. Sets `net.converged` flag.

### Separation of Concerns

| Concern | Separated? | Notes |
|---------|-----------|-------|
| Network Model | Yes | DataFrame model (net.bus, net.gen) cleanly separated from PYPOWER numpy arrays via `_pd2ppc` boundary |
| Problem Formulation | Yes | `makeBdc()` constructs B-matrices independently of solver and data model |
| Solver Interface | Yes | `dcpf()` is a standalone function taking matrices/vectors; OPF uses separate `opf()` function |
| Results | Yes | Dedicated `pandapower.results` module with per-element-type extraction functions |

### Module Sizes

| Module | Lines |
|--------|-------|
| run.py | 551 |
| pd2ppc.py | 486 |
| results.py | 321 |
| makeBdc.py | 172 |
| dcpf.py | 46 |

### Architecture Quality Assessment

**Strengths:**
- Clean DataFrame-to-numpy-array boundary provides a well-defined data model separation
- Reuses proven PYPOWER mathematical core (makeBdc, dcpf, opf are mature code)
- Result DataFrames mirror input DataFrames (net.bus -> net.res_bus) -- intuitive design
- Modular element handling (each element type has its own converter functions)
- In-place modification pattern (toggling `in_service`, changing loads) enables efficient contingency analysis and time-series loops

**Weaknesses:**
- PYPOWER layer is a fork embedded in pandapower, not an external dependency -- creates maintenance burden and makes it harder to upgrade the mathematical core independently
- OPF result dict (containing duals, multipliers, constraint shadow prices) is discarded during result extraction back to DataFrames -- users who need duals must access internal `net._ppc` or monkey-patch the OPF pipeline
- Internal conversion functions (`_pd2ppc`, `_ppci_to_net`) are undocumented private API, creating a barrier for users who need to extend the tool
- Two numbering schemes (external pandapower indices vs internal PYPOWER consecutive indices) add complexity; `_pd2ppc_lookups` is the bridge but is itself undocumented

### Documentation Status

- **Public API:** Fully documented (rundcpp, runpp, rundcopp, runopp) with docstrings and ReadTheDocs
- **Internal interfaces:** Have docstrings but are not in the public API documentation; prefixed with underscore
- **PYPOWER layer:** Has its own documentation inherited from the original PYPOWER project (makeBdc, dcpf, makePTDF)
- **Result schema:** DataFrame columns (p_mw, va_degree, loading_percent, etc.) are documented per element type on ReadTheDocs

## Workarounds

None required. This is a code audit test -- no functional verification needed.

## Timing

- **Wall-clock:** 0.69 s (introspection only, no power flow solve)
- **Timing source:** measured
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pandapower/tests/extensibility/test_b6_code_architecture.py`
