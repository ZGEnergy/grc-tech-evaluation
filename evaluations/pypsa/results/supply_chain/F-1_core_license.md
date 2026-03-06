---
test_id: F-1
tool: pypsa
dimension: supply_chain
status: pass
timestamp: 2026-03-05
---

# F-1: Core License

## Finding

PyPSA is licensed under the MIT License. This is a permissive open-source license with no copyleft obligations.

## Evidence

- **GitHub API:** `gh api repos/PyPSA/PyPSA` returns `"license": {"spdx_id": "MIT"}`
- **PyPI metadata:** License field shows "MIT License"
- **pyproject.toml:** Contains `license = "MIT"` (SPDX identifier)
- **Repository LICENSE file:** Standard MIT License text

The MIT License permits:
- Commercial use
- Modification
- Distribution
- Private use
- Sublicensing

The only obligation is preserving the copyright notice and license text.

**linopy** (core optimization layer, also maintained by PyPSA team): MIT License
**highspy** (HiGHS solver Python bindings): MIT License

## Implications

The core package license is fully permissive and poses no supply chain risk. No copyleft contamination from the main package itself. However, see F-3 for dependency license concerns (Levenshtein is GPL-2.0).
