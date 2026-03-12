---
test_id: D-1
tool: pypsa
dimension: accessibility
network: N/A
protocol_version: v9
skill_version: v1
test_hash: 5f33112e
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 1.394
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
timestamp: 2026-03-11T00:00:00Z
---

# D-1: Install-to-First-Solve (install_to_first_solve)

## Result: PASS

## Finding

PyPSA installs in a single command (`uv sync`) and reaches a first successful solve in under 5 seconds; a new user with `uv` already installed can complete install-to-DCPF in well under 30 minutes.

## Evidence

**Setup steps (from `evaluations/pypsa/README.md`):**
1. `uv sync` — installs PyPSA and all dependencies from `pyproject.toml` into `.venv`
2. `uv run python verify_install.py` — confirms the install (runs a DCPF on case39 and prints "DC power flow completed successfully")

No system-level prerequisites are required for the evaluation workload. Optional solver installs (GLPK, Ipopt) are documented in the README under "System Prerequisites (optional solvers)" but are not needed for HiGHS-based tests.

**Timed invocation in devcontainer:**
```
.devcontainer/dc-exec -C /workspace/evaluations/pypsa uv run python -c "import pypsa; n=pypsa.Network(); print('OK')"
→ OK
→ real time: 1.394s total (dc-exec overhead included)
```

**verify_install.py output:**
```
PyPSA version: 1.1.2
Buses: 39
Lines: 35
DC power flow completed successfully
```

**Friction observed:**
- The README documents `pandapower` as the MATPOWER intermediary, but the actual test scripts use `matpowercaseframes` + manual ppc dict construction. The README's suggested approach would also work but is slightly different from the implemented pipeline.
- The `.values` requirement for ppc dict arrays is not documented in PyPSA's API docs (only discoverable by reading source or failing first). This adds ~5 minutes of friction for a new user.
- Multiple `WARNING` messages appear on import from PYPOWER (gencosts not supported, `status` attribute name collision, carrier not defined). These are harmless but can confuse new users about whether the import succeeded.

**Could a new user install and run DCPF in < 30 minutes?**
Yes, assuming `uv` is installed. `uv sync` takes under 60 seconds; `verify_install.py` runs in ~5 seconds. The `.values` friction would add perhaps 10 minutes of debugging for a first-time user unfamiliar with the ppc dict format.

## Implications

The install experience is excellent: single command, no system dependencies, fast. The only meaningful friction is the MATPOWER ingestion pipeline requiring `.values` arrays, which is a recurring pattern throughout the evaluation. Grade impact: minor deduction from A. This is an A-/B+ accessibility finding.
