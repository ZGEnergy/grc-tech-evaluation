---
test_id: F-7
tool: pandapower
dimension: supply_chain
network: N/A
status: informational
workaround_class: null
timestamp: 2026-03-13T00:00:00Z
protocol_version: v11
skill_version: v2
test_hash: "080ee087"
---

# F-7: Air-Gapped Installation Feasibility

## Summary

pandapower and all core dependencies can be installed offline via pre-downloaded wheels.
No network access is required at runtime for core functionality. The optional
PandaModels.jl bridge requires Julia package downloads but is not needed for standard
use. **Grade: A.**

## Findings

### Core Dependencies

pandapower has 10 core runtime dependencies, all pure-Python or widely available as
pre-built wheels:

| Package            | Constraint     | Wheel Availability |
|--------------------|----------------|--------------------|
| pandas             | ~=2.3          | Universal wheels    |
| networkx           | ~=3.4          | Pure Python         |
| scipy              | <1.17          | Platform wheels     |
| numpy              | >=1.26, <2.4   | Platform wheels     |
| packaging          | ~=25.0         | Pure Python         |
| tqdm               | ~=4.67         | Pure Python         |
| deepdiff           | ~=8.6          | Pure Python         |
| geojson            | ~=3.2          | Pure Python         |
| typing_extensions  | ~=4.9          | Pure Python         |
| pandera            | ~=0.26.1       | Pure Python         |

All dependencies are available from PyPI and can be collected with
`pip download pandapower` for offline transfer. pandapower itself is a pure-Python
wheel (`py3-none-any`), requiring no compilation on the target system.

### Offline Installation Procedure

```bash
# On internet-connected machine:
pip download pandapower -d ./pandapower_wheels

# Transfer ./pandapower_wheels to air-gapped machine, then:
pip install --no-index --find-links ./pandapower_wheels pandapower
```

### Runtime Network Access

Inspection of the pandapower source code confirms no network access is performed at
runtime. The `networks` module, power flow solver, and OPF solver all operate on
local data structures without HTTP calls, downloads, or remote API access.

### PandaModels.jl Bridge (Optional)

The optional `[pandamodels]` extra installs `juliacall~=0.9`, which bridges to Julia's
PandaModels.jl package. This bridge:

- Requires Julia to be installed separately
- Requires `Pkg.add("PandaModels")` which downloads from the Julia General registry
- Is NOT needed for standard power flow or OPF — pandapower's internal PYPOWER-based
  solver handles both without external dependencies

For air-gapped deployments, the PandaModels bridge can simply be omitted. It provides
alternative OPF formulations but is not required for any core functionality.

### Optional Performance Extras

The `[performance]` extra adds `numba`, `lightsim2grid`, and `ortools`. These are
optional accelerators, not functional requirements. All can be pre-downloaded as wheels
if needed.

## Risks

None for core functionality. The PandaModels.jl bridge adds Julia ecosystem complexity
but is entirely optional.
