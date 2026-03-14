---
test_id: P2-1
tool: pandapower
dimension: p2_readiness
network: N/A
status: informational
workaround_class: null
timestamp: 2026-03-13T00:00:00Z
protocol_version: "v10"
skill_version: "v1"
test_hash: "fc0f1dc7"
---

# P2-1: PSS/E RAW Parsing

## Question

Does pandapower support reading PSS/E RAW files?

## Finding

**No.** pandapower 3.4.0 has no PSS/E RAW file parser.

### What was checked

1. **`pandapower.converter` subpackages** — contains `matpower`, `pypower`, `cim`,
   `jao`, `powerfactory`, `ucte`, and `pandamodels`. No `psse` or `raw` subpackage.
2. **Top-level namespace** — no `from_psse`, `from_raw`, or similar function.
   Import/export functions cover JSON, pickle, Excel, SQLite, PostgreSQL only.
3. **`pkgutil.walk_packages`** — recursive scan of all pandapower modules found no
   module with "psse" or "raw" in the name (the one hit, `get_raw_data_from_pickle`,
   is a generic pickle reader unrelated to PSS/E).
4. **`pandapower.converter.psse`** — explicit import raises `ImportError`.

### Supported import formats

| Format | Module |
|--------|--------|
| MATPOWER (.m) | `pandapower.converter.matpower` |
| PYPOWER (ppc dict) | `pandapower.converter.pypower` |
| CIM/CGMES (XML) | `pandapower.converter.cim` |
| PowerFactory | `pandapower.converter.powerfactory` |
| UCTE-DEF | `pandapower.converter.ucte` |
| JAO Static Grid | `pandapower.converter.jao` |

### Effort estimate for Phase 2

To ingest PSS/E RAW files into pandapower, the recommended path is:

1. **Use a third-party parser** (e.g., `grg-psse`, `andes`, or `GridCal`'s RAW parser)
   to parse the RAW file into an intermediate data structure.
2. **Map the parsed data** to pandapower element tables (bus, branch, gen, load, shunt,
   transformer, switched shunt, etc.).
3. **Handle PSS/E-specific constructs** not natively modeled in pandapower (e.g.,
   three-winding transformers with impedance correction, FACTS devices, multi-section
   lines, zone/area/owner records).

Estimated effort: **medium-high** (2-4 weeks for a production-quality converter
supporting RAW v30-v33, depending on element coverage requirements). The MATPOWER
converter provides a template for the mapping layer.

An alternative low-effort path: convert RAW to MATPOWER `.m` format using an external
tool (e.g., MATPOWER's `psse2mpc` in Octave), then import via the existing MATPOWER
converter. This adds a dependency but avoids writing a custom parser.
