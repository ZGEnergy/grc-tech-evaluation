---
test_id: F-1
tool: powermodels
dimension: supply_chain
status: pass
timestamp: 2026-03-05
---

# F-1: Core License

## Finding

PowerModels.jl is released under a BSD 3-Clause license (LANL variant), which is fully permissive and compatible with commercial and government use. The license includes standard U.S. Government rights provisions under DOE contract DE-AC52-06NA25396.

## Evidence

**License text** (from `LICENSE.md` in repo):

```

Copyright (c) 2016, Los Alamos National Security, LLC
All rights reserved.
Copyright 2016. Los Alamos National Security, LLC.
This software was produced under U.S. Government contract DE-AC52-06NA25396
for Los Alamos National Laboratory (LANL)...

```

Key provisions:
1. Redistributions of source code must retain copyright notice
2. Redistributions in binary form must reproduce copyright notice
3. Neither LANL name nor contributors' names may be used to endorse derived products without permission

This is a standard BSD 3-Clause license with LANL/DOE-specific preamble. The LANL code designation is LA-CC-15-024.

**SPDX identifier**: BSD-3-Clause (GitHub reports "NOASSERTION" due to the LANL-specific preamble, but the license body is textually BSD-3-Clause).

**Key dependencies' licenses**:
- JuMP.jl: MPL-2.0 (permissive, file-level copyleft)
- InfrastructureModels.jl: BSD (LANL)
- HiGHS: MIT
- Ipopt: EPL-2.0 (weak copyleft, permissive for linking)
- SCIP: Apache-2.0
- GLPK: GPL-3.0 (strong copyleft -- see F-8)

Source: <https://github.com/lanl-ansi/PowerModels.jl/blob/master/LICENSE.md>

## Implications

The BSD-3-Clause core license is fully permissive and presents no supply chain risk. The LANL/DOE preamble adds government rights language but does not restrict use. The GLPK GPL-3.0 dependency is the only license concern in the stack and is addressed in F-8 (it is optional and replaceable with MIT-licensed HiGHS).
