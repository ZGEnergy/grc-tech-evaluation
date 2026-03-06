---
test_id: P2-1
tool: pypsa
dimension: p2_readiness
status: informational
timestamp: 2026-03-05
---

# P2-1: PSS/E RAW Format Parsing Capability

## Finding

PyPSA has no native PSS/E RAW format parser. It can import networks from pandapower or PYPOWER formats, which themselves can parse RAW files, creating an indirect path.

## Evidence

**PyPSA import methods** (from `dir(n)` on a Network instance):
- `import_from_csv_folder` -- PyPSA native CSV format
- `import_from_excel` -- Excel workbook
- `import_from_hdf5` -- HDF5 archive
- `import_from_netcdf` -- NetCDF file
- `import_from_pandapower_net` -- pandapower network object
- `import_from_pypower_ppc` -- PYPOWER PPC dict

No `import_from_raw`, `import_from_psse`, or similar method exists.

**Module scan:** No modules matching "raw" or "psse" found in `pypsa.*` namespace.

**Indirect path via pandapower:**
1. pandapower has `pandapower.converter.from_ppc()` and can read some PSS/E formats
2. Convert pandapower net to PyPSA: `n.import_from_pandapower_net(net)`
3. This indirect path has limitations -- not all PSS/E features (e.g., dynamic models, relay settings) translate through pandapower

**Indirect path via MATPOWER/PYPOWER:**
1. Use MATPOWER or a third-party PSS/E-to-MATPOWER converter
2. Load the MATPOWER case into a PYPOWER PPC dict
3. Import via `n.import_from_pypower_ppc(ppc)`

**Third-party options:**
- `matpowercaseframes` (included in eval dependencies) parses MATPOWER `.m` files but not PSS/E RAW
- The `andes` package has a PSS/E parser but is not a PyPSA dependency

## Implications

PSS/E RAW parsing would require either extending PyPSA or using a converter pipeline (PSS/E -> pandapower/PYPOWER -> PyPSA). This is a gap for organizations with existing PSS/E model libraries. For Phase 2, a custom RAW parser or integration with an existing parser library would be needed.
