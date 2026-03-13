---
test_id: D-3
tool: pypsa
dimension: accessibility
network: N/A
protocol_version: v9
skill_version: v1
test_hash: 361c35df
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

# D-3: Example Verification (example_verification)

## Result: PASS

## Finding

The evaluation project's `verify_install.py` script runs successfully and unmodified. No bundled tutorial notebooks are present in `evaluations/pypsa/` beyond `verify_install.py`. Official PyPSA documentation examples at https://pypsa.readthedocs.io/ are referenced but not bundled locally.

## Evidence

**Local scripts inventory:**
```
evaluations/pypsa/
├── verify_install.py      ← only example script present
├── pyproject.toml
├── uv.lock
└── tests/
    └── expressiveness/    ← evaluation test scripts (not official examples)
```

**`verify_install.py` execution:**
```bash
.devcontainer/dc-exec -C /workspace/evaluations/pypsa uv run python verify_install.py
```
Output:
```
WARNING:pypsa.network.io:Warning: Note that when importing from PYPOWER, some PYPOWER features not supported: areas, gencosts, component status
[status attribute warnings]
INFO:pypsa.network.power_flow:Performing linear load-flow on AC sub-network...
PyPSA version: 1.1.2
Buses: 39
Lines: 35
DC power flow completed successfully
```
Status: **pass unmodified**

**Script content:** Loads case39.m via matpowercaseframes, constructs ppc dict, imports to PyPSA, runs `n.lpf()`, and prints summary stats. All operations succeed without modification.

**Official examples from docs (not locally bundled):**
- https://pypsa.readthedocs.io/en/latest/examples/ — links to Jupyter notebooks hosted on GitHub
- Notable examples: "Optimal Power Flow with Pyomo backend", "Unit Commitment", "Storage dispatch", "Minimal example"
- These are online-only; not accessible offline or locally

**Friction observed:**
- The only local example is `verify_install.py`, which is minimal. Official tutorials require internet access to the docs/GitHub.
- No local Jupyter notebooks or self-contained example scripts beyond the verify script.
- The WARNING messages on startup are numerous (5+ warnings per import) — a new user might not know whether these are expected.

## Implications

The verify script runs unmodified, confirming the install is functional. The lack of bundled offline examples is a minor accessibility gap — official documentation examples are online-only. The WARNING noise during `import_from_pypower_ppc` is cosmetic but could confuse new users. Grade impact: minor; B+ level.
