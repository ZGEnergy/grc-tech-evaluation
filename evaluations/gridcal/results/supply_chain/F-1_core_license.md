---
test_id: F-1
tool: gridcal
dimension: supply_chain
network: N/A
status: informational
workaround_class: null
protocol_version: "v10"
skill_version: v1
test_hash: "e56461f2"
timestamp: "2026-03-13T23:00:00Z"
---

# F-1: Core License

## Finding

VeraGridEngine is licensed under the Mozilla Public License 2.0 (MPL-2.0). This is a weak copyleft license that requires modifications to MPL-2.0 files to be shared under the same license, but permits combining with proprietary code in larger works without requiring the proprietary code to be open-sourced.

## Evidence

**License identification:**
- GitHub API reports: `MPL-2.0`
- PyPI metadata: `MPL2`
- LICENSE file header: "Mozilla Public License Version 2.0"
- Source file headers: `# This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.`
- SPDX identifier in source: `SPDX-License-Identifier: MPL-2.0`

**License history:**
- Original license (2016): LGPL (per LICENSE commit history)
- Current license: MPL-2.0 (changed circa November 2024, per research-context.md)
- The LICENSE file has had 5 commits since repo creation, with the most recent substantive change establishing MPL-2.0

**MPL-2.0 key properties:**
- File-level copyleft: modifications to existing MPL-2.0 files must remain MPL-2.0
- Larger works: MPL-2.0 code can be combined with proprietary code without triggering copyleft on the proprietary portions
- Patent grant: contributors grant patent licenses for their contributions
- Compatible with Apache-2.0 and GPL (Section 3.3)

**Comparison to previous license (LGPL):**
- LGPL required dynamic linking for proprietary use; MPL-2.0 is more permissive
- The license change from LGPL to MPL-2.0 removed the dynamic linking requirement, simplifying integration into proprietary systems

## Implications

MPL-2.0 is generally compatible with enterprise adoption. It is more permissive than LGPL for integration purposes (no dynamic linking requirement) while still requiring that modifications to VeraGridEngine source files themselves remain open. For an evaluator consuming the library as a dependency without modifying its source, MPL-2.0 imposes no copyleft obligations on the consuming application. The license change from LGPL to MPL-2.0 was a positive move for commercial adoption.
