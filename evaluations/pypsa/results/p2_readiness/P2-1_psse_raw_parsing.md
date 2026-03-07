---
test_id: P2-1
tool: pypsa
dimension: p2_readiness
network: null
protocol_version: "v4"
status: informational
workaround_class: null
timestamp: 2026-03-06T00:00:00Z
---

# P2-1: PSS/E RAW Parsing

## Capability: No

PyPSA has no native PSS/E RAW format parser. A codebase search of PyPSA v1.1.2's source tree (`pypsa/`) returned zero references to PSS/E, RAW, or any related parser module.

## Pandapower Bridge

Pandapower (v2.x, installed in the evaluation environment) was investigated as a potential bridge path. Pandapower's `converter/` module supports MATPOWER, PyPOWER, CIM, UCTE, PowerFactory, and Jao formats -- but **not** PSS/E RAW. A recursive search of the entire pandapower package for `psse`, `PSS/E`, `from_psse`, `read_raw`, or `raw_to` returned zero results.

Therefore, the pandapower import bridge (`n.import_from_pandapower_net()`) cannot be used to ingest PSS/E RAW files because pandapower itself lacks a RAW parser.

## Supported RAW Versions

Not applicable -- no parser exists.

## Alternative Import Paths

| Format | PyPSA Support | Notes |
|--------|--------------|-------|
| MATPOWER .m | Via matpowercaseframes + PPC dict | Working, tested in A-1 through A-11 |
| PyPOWER PPC dict | `n.import_from_pypower_ppc()` | Native, drops gencost |
| pandapower net | `n.import_from_pandapower_net()` | Beta, no PSS/E in pandapower |
| CSV folder | `n.import_from_csv_folder()` | Native |
| NetCDF | `n.import_from_netcdf()` | Native |
| HDF5 | `n.import_from_hdf5()` | Native |
| PSS/E RAW | Not supported | No parser in PyPSA or pandapower |

## Estimated Effort to Add

Adding PSS/E RAW parsing would require:

1. **External library approach (low effort, ~1-2 days):** Use a third-party RAW parser (e.g., `grg-psse`, `andes`, or AMES) to parse the RAW file into a bus/branch/gen data structure, then map to PyPSA components manually. This is analogous to the existing matpowercaseframes pipeline.

2. **Native parser approach (high effort, ~2-4 weeks):** Implement a RAW parser from scratch within PyPSA. PSS/E RAW is a fixed-width, version-dependent format (versions 26-35+) with significant complexity in transformer modeling, switched shunt encoding, and multi-section lines.

3. **Key mapping challenges:**
   - PSS/E RAW uses a different transformer model (two-winding and three-winding with tap/phase shift parameters that differ from MATPOWER conventions)
   - Switched shunt blocks require translation to PyPSA's ShuntImpedance component
   - Area interchange and zone data have no direct PyPSA equivalent
   - Owner/operator fields are metadata-only (no PyPSA mapping needed)

The external library approach is the most practical path. No open GitHub issues or PRs request PSS/E RAW support in PyPSA.
