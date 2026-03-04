---
tool: pypsa
dimension: supply_chain
tags: [license-flags]
severity: low
timestamp: 2026-03-04T12:00:00Z
---
# Observation: GPL-2.0-or-later dependency (Levenshtein)

## Summary
PyPSA declares `levenshtein>=0.27.1` as a **direct, non-optional** dependency. The `Levenshtein` package (v0.27.3) is licensed under GPL-2.0-or-later, a strong copyleft license.

## Usage context
The dependency is used in exactly one location:

```python
# pypsa/network/transform.py
from Levenshtein import distance
```

It computes edit distance to suggest corrections when users mistype attribute names (e.g., "p_nom_max" vs "p_nom_mxa"). This is a developer UX convenience feature, not part of the power flow computation or optimization path.

## Risk assessment
- **Copyleft risk:** Under strict GPL interpretation, linking GPL code into a combined work may require the entire work to be distributed under GPL. However, this depends on the distribution model (internal use vs. redistribution).
- **Internal use only:** If ZGE uses PyPSA internally without redistributing modified source, GPL obligations are not triggered.
- **Replaceable:** The `RapidFuzz` package (MIT-licensed, already installed as a transitive dep of `Levenshtein`) provides `rapidfuzz.distance.Levenshtein.distance()` as a drop-in replacement.

## Remediation options
1. **No action needed** if PyPSA is used internally without redistribution
2. **Patch pypsa** to use `rapidfuzz.distance.Levenshtein.distance` instead of `Levenshtein.distance` (one-line change)
3. **Upstream contribution**: propose the swap to PyPSA maintainers (RapidFuzz is already a transitive dependency)

## Verdict
Low severity. Does not affect the supply chain gate assessment. The GPL code is isolated to a non-critical UX helper and is trivially replaceable.
