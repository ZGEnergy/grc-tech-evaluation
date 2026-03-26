---
observation_type: license-flags
source_test: F-1
source_dimension: supply_chain
tool: gridcal
severity: low
timestamp: "2026-03-24T18:00:00Z"
---

# License Flag: MPL-2.0 (Weak Copyleft)

## Summary

VeraGridEngine is licensed under MPL-2.0, a weak (file-level) copyleft license. Modifications to VeraGridEngine source files must be shared under MPL-2.0, but consuming the library without modification imposes no copyleft obligations on the consuming application.

## Details

- **License:** MPL-2.0 (Mozilla Public License 2.0)
- **Copyleft scope:** File-level only (weaker than LGPL)
- **Impact on consuming application:** None, when used as an unmodified dependency
- **Patent grant:** Yes (contributors grant patent licenses)
- **GPL compatible:** Yes (Section 3.3)

## Risk Assessment

**Low risk** for enterprise adoption as a library dependency. MPL-2.0 file-level copyleft only triggers if the consuming application modifies VeraGridEngine source files and distributes the modified version. Standard usage (importing as a library) does not trigger any distribution obligations.
