---
test_id: F-1
tool: powermodels
dimension: supply_chain
network: N/A
protocol_version: "v4"
status: pass
workaround_class: null
timestamp: 2026-03-06T00:00:00Z
---

# F-1: Core License

## Result: PASS

## Finding

PowerModels.jl v0.21.5 is licensed under BSD-3-Clause with U.S. Government rights (DOE contract DE-AC52-06NA25396). This is a permissive, non-copyleft license fully compatible with commercial use.

## Evidence

LICENSE.md text from installed package at `/opt/julia-depot/packages/PowerModels/VCmhH/LICENSE.md`:

> Copyright (c) 2016, Los Alamos National Security, LLC
> All rights reserved.
> Copyright 2016. Los Alamos National Security, LLC. This software was produced under U.S. Government contract DE-AC52-06NA25396 for Los Alamos National Laboratory (LANL)...

The license explicitly grants redistribution and use in source and binary forms with the standard three BSD conditions (attribution, binary reproduction, no endorsement without permission).

Project.toml confirms: `version = "0.21.5"`, repo at `<https://github.com/lanl-ansi/PowerModels.jl`.>

The README footer states: "This code is provided under a BSD license as part of the Multi-Infrastructure Control and Optimization Toolkit (MICOT) project, C15024."

## Implications

BSD-3-Clause is one of the most permissive OSS licenses. No copyleft concerns for the core package itself. The U.S. Government rights clause is standard for DOE-funded software and does not restrict commercial use by third parties.
