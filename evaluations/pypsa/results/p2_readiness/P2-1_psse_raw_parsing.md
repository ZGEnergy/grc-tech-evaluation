---
test_id: P2-1
tool: pypsa
dimension: p2_readiness
network: N/A
protocol_version: v11
skill_version: v2
test_hash: 9f8ed88f
status: informational
workaround_class: null
timestamp: 2026-03-24T16:00:00Z
---

# P2-1: PSS/E RAW Parsing Capability

## Result: INFORMATIONAL — No native capability

## Capability Assessment

**Native PSS/E RAW parsing: No.**

PyPSA v1.1.2 has no native capability to parse PSS/E RAW format files in any
version (v30, v31, v33, v34). This was confirmed by inspection of the six public `import_from_*` methods
on `pypsa.Network`. PyPSA's six import methods
(`import_from_csv_folder`, `import_from_pypower_ppc`, `import_from_pandapower_net`,
`import_from_hdf5`, `import_from_netcdf`, `import_from_excel`) all expect
PyPSA-native data layouts, PYPOWER PPC dictionaries, or pandapower network
objects — none accept PSS/E record types.

**Supported RAW versions: None.**

## Bridge Options Assessed

### pandapower bridge

Pandapower v3.4.0 (installed in the devcontainer) also lacks a PSS/E RAW parser.
The `pandapower.converter` module contains only `pandamodels`; there is no
`from_psse()` function. A `pkgutil.walk_packages` search of the entire
pandapower package tree found no PSS/E-related modules. Therefore the
pandapower bridge path (`raw -> pandapower -> pypsa`) is not viable without
adding a third-party PSS/E parser.

### Third-party PSS/E parsers

Two open-source options exist for the first stage of a bridge:

1. **grg-psse** (LANL, BSD-3): Python library that parses PSS/E RAW v30–v33
   files into structured Python objects. Mapping from grg-psse data structures
   to PyPSA components would require a custom converter covering buses,
   branches, generators, loads, transformers (2W and 3W), switched shunts,
   and FACTS devices.

2. **andes** (CURENT, GPL-3): Full power system simulator with a PSS/E RAW
   parser. The GPL-3 license may be incompatible with proprietary workflows.

### Custom parser

Writing a PSS/E RAW parser from scratch and mapping to PyPSA components is
estimated at 2–4 weeks of development effort for a single RAW version, covering:

- Fixed-format record parsing (80-column card images for v30; free-format for v33+)
- Bus, load, generator, branch, transformer, switched shunt, and area records
- Mapping PSS/E fields (I, J, K, CKT, IDE, STATUS) to PyPSA attributes
- Handling PSS/E-specific features not natively supported by PyPSA:
  three-winding transformers (issue #643, wontfix), phase-shifting
  transformers (issue #456, open), FACTS devices, multi-terminal DC lines

## Effort Estimate to Add PSS/E Support

| Approach | Effort | Risk |
|----------|--------|------|
| grg-psse bridge (recommended) | 1–2 weeks | Medium — grg-psse covers v30–v33 but not v34; mapping 3W transformers requires decomposition since PyPSA only supports 2W |
| Custom parser | 2–4 weeks | High — PSS/E format has undocumented quirks and version-specific differences |
| andes bridge | 1 week | High — GPL-3 license contamination risk |

The grg-psse bridge is the most practical path. The core mapping (buses,
branches, generators, loads, 2W transformers) is straightforward. The main
complexity is in PSS/E features that PyPSA does not model natively (3W
transformers, PSTs, FACTS), which would need to be either approximated or
dropped with warnings.

## Sources

1. PyPSA v1.1.2 API surface inspection — six `import_from_*` methods enumerated (verified in devcontainer 2026-03-24)
2. pandapower v3.4.0 converter module inspection — no `from_psse` function
3. grg-psse: https://github.com/lanl-ansi/grg-psse (BSD-3, LANL)
4. PyPSA issue #643 (three-winding transformers, wontfix)
5. PyPSA issue #456 (phase-shifting transformers, open)
