---
observation_type: license-flags
source_test: F-3
source_dimension: supply_chain
tool: gridcal
severity: low
timestamp: "2026-03-24T18:00:00Z"
---

# License Flag: LGPL Dependencies (chardet, moocore)

## Summary

Two dependencies use LGPL-2.1-or-later: `chardet` (direct dependency, pure Python) and `moocore` (transitive via pymoo, has compiled C extension). Both are weak copyleft. No GPL, AGPL, or proprietary licenses found in the dependency tree.

## Flagged Packages

1. **chardet 6.0.0.post1** -- LGPL-2.1-or-later
   - Role: character encoding detection for file I/O
   - Type: pure Python (no compiled code)
   - Relationship: direct dependency of veragridengine
   - Mitigation: replaceable with `charset-normalizer` (MIT)

2. **moocore 0.2.0** -- LGPL-2.1-or-later
   - Role: multi-objective optimization core (Pareto front computation)
   - Type: compiled C extension via cffi
   - Relationship: transitive dependency (veragridengine -> pymoo -> moocore)
   - Mitigation: only exercised by pymoo multi-objective features, not core power flow

## Risk Assessment

**Low risk.** Both LGPL packages are consumed as unmodified libraries. Python import is not considered "linking" in the LGPL sense for pure-Python packages (chardet). For moocore (compiled), LGPL-2.1 allows use via dynamic linking, which is the standard Python import mechanism. Neither package is in the critical path for power flow or OPF functionality.
