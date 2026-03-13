---
test_id: F-1
tool: powermodels
dimension: supply_chain
network: N/A
status: pass
workaround_class: null
timestamp: "2026-03-11T00:00:00Z"
protocol_version: "v9"
skill_version: v1
test_hash: "64a1874e"
---

# F-1: Identify license of the main package

## Finding

PowerModels.jl is released under a BSD 3-Clause-style license issued by Los Alamos National Security, LLC (U.S. Government origin). It is permissive, non-copyleft, and allows commercial use without source disclosure.

## Evidence

License file: `/opt/julia-depot/packages/PowerModels/VCmhH/LICENSE.md`

Key text:
- Copyright holder: Los Alamos National Security, LLC (contract DE-AC52-06NA25396, DOE/LANL)
- Three redistribution conditions: (1) retain copyright notice, (2) reproduce notice in binary distributions, (3) no use of LANL/contributor names for endorsement without permission
- No copyleft clause; no viral distribution requirements
- Standard BSD 3-Clause disclaimer of warranty

The license is substantively equivalent to BSD 3-Clause. The government-origin boilerplate ("The U.S. Government has rights to use, reproduce, and distribute this software") is standard for DOE/LANL releases and does not restrict commercial use by third parties.

Verified version: PowerModels 0.21.5 (git-tree-sha1: `b8e410e1d827b621e82e7e670967f0efc5845c30`)

## Implications

No copyleft risk and no proprietary restrictions. The license is permissive and compatible with commercial deployment. No legal review required for the main package license itself.
