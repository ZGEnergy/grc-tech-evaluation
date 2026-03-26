---
test_id: F-2
tool: matpower
dimension: supply_chain
network: N/A
protocol_version: "v11"
skill_version: v2
test_hash: b6b0a920
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

# F-2: Dependency Tree

## Result: PASS

## Finding

MATPOWER 8.1 bundles all required dependencies within its distribution archive. There are zero external runtime dependencies beyond MATLAB or GNU Octave itself. The dependency tree is flat (depth 1) with 4 bundled sub-packages. No package manager is involved -- installation is a manual download-and-extract operation.

## Evidence

**Bundled sub-packages (all included in `matpower8.1.zip`):**

| Package | Version | Role |
|---------|---------|------|
| MP-Test (mptest) | 8.1 | Unit testing framework |
| MIPS | 1.5.2 | Built-in interior-point solver |
| MP-Opt-Model | 5.0 | Optimization model builder |
| MOST | 1.3.1 | Multi-period optimal scheduling |

**Extras (optional, also bundled):**

| Package | Description |
|---------|-------------|
| SynGrid | Synthetic grid generation |
| SDP_PF | Semidefinite programming power flow |
| smartmarket | Market simulation |
| state_estimator | State estimation |
| reduction | Network reduction |
| maxloadlim | Maximum loadability limit |
| simulink_matpower | Simulink integration |

**Dependency tree metrics:**
- Total direct dependencies: 4 (all bundled)
- Tree depth: 1
- Transitive dependencies: 0 (flat tree)
- Unresolvable dependencies: 0
- External package manager dependencies: 0

**Verification command:**
```
octave --eval "addpath(genpath('/workspace/evaluations/matpower/matpower8.1')); mpver"
```
Output confirms all 4 bundled packages are detected and versioned.

## Implications

The fully self-contained distribution model is ideal for supply chain control. There is no dependency resolution step, no network fetch at install time, and no risk of transitive dependency conflicts. The entire dependency tree is auditable from the single distribution archive.
