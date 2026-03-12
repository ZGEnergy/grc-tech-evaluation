---
test_id: P2-1
tool: pypsa
dimension: p2_readiness
network: N/A
protocol_version: v9
skill_version: v1
test_hash: e75a0cfb
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
timestamp: 2026-03-11T00:00:00Z
---

# P2-1: PSS/E RAW Parsing

## Result: INFORMATIONAL

## Finding

PyPSA 1.1.2 has no native PSS/E RAW import capability, and the pandapower 3.4.0 installation (available as a bridge via `n.import_from_pandapower_net()`) also lacks PSS/E import. RAW file ingestion would require adding a third-party parser library and writing a custom mapping layer.

## Evidence

**PyPSA native import methods confirmed via introspection:**

```bash
$ python -c "import pypsa; n = pypsa.Network(); print([m for m in dir(n) if 'import' in m.lower()])"
['_import_components_from_df', '_import_from_importer', '_import_series_from_df',
 '_read_in_default_standard_types', 'import_from_csv_folder', 'import_from_excel',
 'import_from_hdf5', 'import_from_netcdf', 'import_from_pandapower_net',
 'import_from_pypower_ppc']
```

No PSS/E or RAW-related method appears. The six public import methods are:
- `import_from_pypower_ppc` — PyPOWER dict (used throughout this evaluation)
- `import_from_pandapower_net` — pandapower Network object
- `import_from_csv_folder` / `import_from_excel` / `import_from_hdf5` / `import_from_netcdf` — PyPSA's own serialization formats

**Source code search confirms no PSS/E support:**

```bash
$ grep -ri 'psse\|raw_file\|pss.e\|pss_e' \
    .venv/lib/python3.12/site-packages/pypsa/ --include='*.py' -l
(no output — zero matches)
```

**Pandapower bridge assessment:**

`pandapower` 3.4.0 is installed (available as bridge). Its top-level namespace and all converter submodules were searched for PSS/E methods:

```bash
$ grep -ri 'psse\|from_psse\|from_raw\|read_raw' \
    .venv/lib/python3.12/site-packages/pandapower/ --include='*.py' -l
/workspace/.../pandapower/converter/ucte/ucte_parser.py   # only UCTE, not PSS/E
```

The UCTE parser contains one incidental mention of "pss/e" in a comment. There is no `from_psse`, `read_psse_raw`, or equivalent in pandapower 3.4.0. The `pandapower.converter` package contains: matpower, pypower, powerfactory (DIgSILENT), CIM/CGMES, JAO, UCTE — but not PSS/E RAW.

**No third-party PSS/E Python parser available in the environment:**

```python
import psse35    # ModuleNotFoundError
import esa       # ModuleNotFoundError (Easy SimAuto)
import py_psse   # ModuleNotFoundError
import rawpy     # ModuleNotFoundError (image library, not power systems)
```

**Effort estimate to add PSS/E RAW support:**

The standard approach would be to use `pypsa-psse` (PyPI: not published as of 2026-02) or implement a custom parser. A minimum viable RAW-to-PyPSA bridge would require:

1. **RAW parser** (~300–500 LOC or third-party library): Parse RAW v30/v33/v35 fixed-format sections (SYSTEM, BUS, LOAD, GENERATOR, BRANCH, TRANSFORMER). Libraries `gridcal` or `pandapower.psslib` (the latter exists only in pandapower's GitHub `develop` branch, not the PyPI release) could be adapted.
2. **Mapping layer** (~200–400 LOC): Convert PSS/E bus/branch data to PyPSA's DataFrame-based data model. PSS/E uses flat indexed records; PyPSA expects pandas DataFrames with named indices. The main mapping complexity is transformer modeling (3-winding, tap ratio, phase shift) and the bus voltage/angle reference convention.
3. **Validation**: PSS/E uses MVA base per area; PyPSA uses a global `n.sn_mva` base. Cross-area base conversion is error-prone.

**Estimated total effort:** 4–8 developer-days for a production-quality bridge covering RAW v33 (the most common utility format), or 1–2 developer-days for a minimal bridge covering bus/branch/generator (no 3-winding transformers, HVDC, facts). No blocking technical barriers exist — the data structures are compatible and PyPSA's `n.add()` API is well-suited to programmatic population.

**Comparison to MATPOWER path:** The current MATPOWER path via `pypower`/`matpowercaseframes` is straightforward (used in G-1 through G-3, A-1 through A-12 of this evaluation). PSS/E RAW would require comparable effort to the matpower bridge but with higher format complexity due to PSS/E's versioned fixed-format sections.

## Phase 2 Implications

If PyPSA is selected for Phase 2, real-world production networks will likely be supplied in PSS/E RAW format (the industry standard in U.S. ISOs/RTOs). This gap means:

- **No out-of-the-box RAW ingestion.** A custom parser or third-party library must be procured and integrated before any Phase 2 test that uses a production-representative network topology.
- **Risk:** RAW format versioning (v30 vs v33 vs v35) introduces parsing fragility. Different ISOs use different versions and vendor extensions.
- **Mitigation:** The pandapower team has a `psse` converter in their development branch (`pandapower.converter.psse`) that could be backported; alternatively, a minimal bus/branch/generator parser is achievable in 1–2 developer-days and sufficient for DCPF/DCOPF tasks that do not require reactive power or transformer tap modeling.
- **MATPOWER path remains viable** for Phase 2 if case files can be provided in .m format — all Phase 1 tests succeeded using this path with zero failures at the ingestion layer.
