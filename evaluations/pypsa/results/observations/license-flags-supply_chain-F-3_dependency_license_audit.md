---
tag: license-flags
source_dimension: supply_chain
source_test: F-3
tool: pypsa
severity: medium
timestamp: 2026-03-24T14:00:00Z
---

# Observation: GPL-2.0-or-later dependency (Levenshtein) in PyPSA dependency chain

## Finding

PyPSA v1.1.2 declares `levenshtein>=0.27.1` as a direct dependency in `pyproject.toml`. The Levenshtein package (v0.27.3 installed) is licensed under GPL-2.0-or-later, confirmed via `License-Expression` metadata field on 2026-03-24.

This is the **only** strong copyleft dependency in PyPSA's entire dependency chain (88 packages audited). Two packages carry MPL-2.0 (weak copyleft): `certifi` (file-level only) and `tqdm` (dual-licensed MPL-2.0 AND MIT).

## Context

The `levenshtein` package is used in PyPSA's component validation code for fuzzy string matching -- when a user mistypes a component attribute name, PyPSA suggests the closest valid attribute. This is a convenience/UX feature, not a computational dependency.

The Levenshtein package depends on `rapidfuzz` (MIT-licensed), which provides the underlying fuzzy matching algorithms. The GPL license applies to the Levenshtein package's own wrapper code and C++ extensions.

## Risk Assessment

- **Internal use only**: GPL imposes no additional obligations when the software is used internally without redistribution.
- **Redistribution**: If ZGE redistributes software incorporating PyPSA (e.g., as part of a delivered product), the GPL-2.0-or-later license on Levenshtein could require the combined work to be distributed under GPL-compatible terms (conservative FSF interpretation).
- **Mitigation available**: The functionality could be replaced with `rapidfuzz` (MIT) directly, or the `levenshtein` dependency could be made optional via a try/except import pattern. This is a one-line code change in PyPSA's source.

## Implications

For supply chain assessment: this is the only copyleft dependency in PyPSA's direct dependency chain. All other dependencies are permissively licensed (MIT, BSD, Apache 2.0, PSF). Legal counsel should evaluate the redistribution implications if applicable to the deployment scenario.
