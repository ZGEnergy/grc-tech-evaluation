---
test_id: F-1
tool: pypsa
dimension: supply_chain
network: N/A
status: pass
workaround_class: null
timestamp: 2026-03-13T12:00:00Z
protocol_version: v10
skill_version: v1
test_hash: c0a27872
---

# F-1: Core License

## Findings

### License Type

**MIT License** (permissive).

Confirmed via:
- PyPI metadata: `License :: OSI Approved :: MIT License`
- `pyproject.toml`: `license = { file = "LICENSE" }` with MIT classifier
- GitHub repository LICENSE file
- SPDX headers in source files: `SPDX-License-Identifier: MIT`

### Full License Text

Standard MIT License with copyright held by "PyPSA Contributors."

### Flags

- **Copyleft**: No. MIT is permissive.
- **Proprietary**: No.
- **Commercial use**: Permitted without restriction.
- **Modification**: Permitted without restriction.
- **Distribution**: Permitted with attribution.

### Note on Dependency License

While PyPSA itself is MIT, the `levenshtein` dependency is GPL-2.0-or-later
(see F-3 for details). This creates a potential copyleft propagation concern
in the dependency chain.

## Recorded Metrics

- license_type: MIT
- flags: none on core package; see F-3 for dependency flag
