---
test_id: F-1
tool: gridcal
dimension: supply_chain
network: N/A
status: pass
workaround_class: null
protocol_version: "v11"
skill_version: v2
test_hash: "e56461f2"
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: null
solver: null
timestamp: "2026-03-24T18:00:00Z"
---

# F-1: Core License

## Result: PASS

## Finding

VeraGridEngine is licensed under the Mozilla Public License 2.0 (MPL-2.0). This is a weak copyleft license: modifications to MPL-2.0 files must be shared under the same license, but the license permits combining with proprietary code in larger works without requiring the proprietary portions to be open-sourced. The license was changed from LGPL to MPL-2.0 circa November 2024 (v5.2.0 release).

## Evidence

**License identification:**
- GitHub API reports: `MPL-2.0` (accessed 2026-03-24)
- PyPI metadata `License` field: `MPL2`
- LICENSE.txt in package: "Mozilla Public License Version 2.0"
- Source file headers: `# This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.`
- SPDX identifier in source files: `SPDX-License-Identifier: MPL-2.0`

**License history:**
- Original license (2016): LGPL
- Current license: MPL-2.0 (changed at v5.2.0, released 2024-11-11, tagged "5.2.0 relicensed to MPLv2")

**MPL-2.0 key properties:**
- File-level copyleft: modifications to existing MPL-2.0 files must remain MPL-2.0
- Larger works: MPL-2.0 code can be combined with proprietary code without triggering copyleft on the proprietary portions
- Patent grant: contributors grant patent licenses for their contributions
- Compatible with Apache-2.0 and GPL (Section 3.3)
- No dynamic linking requirement (unlike LGPL)

**Copyleft flag:** Yes (weak copyleft, file-level only). MPL-2.0 is weaker than LGPL and does not require dynamic linking or source distribution of the consuming application. For typical library consumption (importing without modifying source files), MPL-2.0 imposes no copyleft obligations on the consuming application.

## Implications

MPL-2.0 is generally compatible with enterprise adoption. The file-level copyleft is the weakest form of copyleft in common use. For an organization consuming VeraGridEngine as a dependency without modifying its source files, MPL-2.0 imposes no distribution obligations. The license change from LGPL to MPL-2.0 was a positive move for commercial adoption, removing the dynamic linking requirement.
