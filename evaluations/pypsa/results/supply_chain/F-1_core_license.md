---
test_id: F-1
tool: pypsa
dimension: supply_chain
network: N/A
protocol_version: v9
skill_version: v1
test_hash: 12e210df
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
timestamp: 2026-03-11T00:00:00Z
---

# F-1: Core License (core_license)

## Result: PASS

## Finding

PyPSA v1.1.2 is MIT licensed. The license is confirmed directly from the installed package METADATA in the devcontainer.

## Evidence

**Command:**
```bash
.devcontainer/dc-exec -C /workspace/evaluations/pypsa uv run python -c "import pypsa; print(pypsa.__file__)"
→ /workspace/evaluations/pypsa/.venv/lib/python3.12/site-packages/pypsa/__init__.py
```

**METADATA excerpt:**
```
cat /workspace/evaluations/pypsa/.venv/lib/python3.12/site-packages/pypsa-1.1.2.dist-info/METADATA | head -30
```
Output:
```
Name: pypsa
Version: 1.1.2
License: MIT License

Copyright (c) <year> <copyright holders>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software...
```

**GitHub source:** https://github.com/PyPSA/PyPSA/blob/master/LICENSE — MIT license confirmed at repository level.

**Project homepage:** https://pypsa.org/ states "open source" under MIT.

## Implications

MIT license is permissive, commercial-use-compatible, and imposes no copyleft obligations. No legal barrier to production deployment. This criterion is fully satisfied.
