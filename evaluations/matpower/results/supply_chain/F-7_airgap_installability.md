---
test_id: F-7
tool: matpower
dimension: supply_chain
network: N/A
protocol_version: v10
skill_version: v1
test_hash: eba5e970
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
solver: null
timestamp: 2026-03-14T00:00:00Z
---

# F-7: Air-Gap Installability

## Result: PASS

## Finding

MATPOWER is fully air-gap installable. The entire installation process is: download a zip file, extract it, and add the directory to the MATLAB/Octave path. No package manager, no dependency resolution, no network access at runtime. External solvers require separate installation but are also available as offline-installable packages.

## Evidence

**Installation process (air-gapped):**
1. Pre-download `matpower8.1.zip` (47.3 MB) on a connected machine
2. Transfer to air-gapped environment
3. Extract: `unzip matpower8.1.zip`
4. Add to Octave path: `addpath(genpath('/path/to/matpower8.1'))`
5. Verify: `mpver`

**No runtime network dependencies:**
- No license server checks
- No telemetry or analytics
- No package manager calls
- No dynamic downloads of data or updates
- All case files bundled in distribution

**Solver air-gap status:**

| Solver | Air-gap installable? | Notes |
|--------|---------------------|-------|
| MIPS (built-in) | Yes -- bundled | No separate install needed |
| GLPK | Yes | Packaged in OS repos; pre-install via `apt` on connected machine, then copy |
| IPOPT | Yes | Available as OS package or buildable from source offline |
| HiGHS | Conditional | Not available as Octave binding in current devcontainer; requires manual build |

**Verification:** The `setup.sh` script in the evaluation directory demonstrates the complete offline installation workflow (download, verify checksum, extract). After extraction, MATPOWER functions work immediately with no further network access.

## Implications

MATPOWER's distribution model (single zip archive, no package manager, no runtime network calls) is ideal for air-gapped environments. This is one of the strongest supply chain properties of MATPOWER compared to tools that rely on Python (pip/conda) or Julia (Pkg) package managers, which require network access or complex offline mirror setups.
