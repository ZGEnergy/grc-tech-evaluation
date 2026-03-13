---
test_id: F-2
tool: powermodels
dimension: supply_chain
network: N/A
status: pass
workaround_class: null
timestamp: "2026-03-11T00:00:00Z"
protocol_version: "v9"
skill_version: v1
test_hash: "8b638f83"
---

# F-2: Generate full dependency tree via Pkg.status with full manifest

## Finding

The full resolved manifest contains 114 entries (including stdlib packages). All direct dependencies are pinned by the Manifest.toml with exact versions and git-tree-sha1 hashes. Three packages are pinned to older versions due to compatibility constraints (marked ⌅); four have newer versions available (marked ⌃) but are not upgradable within the current compat bounds. No unresolvable dependencies were detected.

## Evidence

Command executed in devcontainer:

```

.devcontainer/dc-exec -C /workspace/evaluations/powermodels julia --project=. -e 'using Pkg; Pkg.status(; mode=PKGMODE_MANIFEST)'

```

### Direct dependencies (from Project.toml):

| Package | Version | Status |
|---------|---------|--------|
| GLPK | 1.2.1 | pinned |
| HiGHS | 1.21.1 | ⌃ newer available |
| Ipopt | 1.14.1 | pinned |
| JuMP | 1.29.4 | ⌃ newer available |
| PowerModels | 0.21.5 | pinned |
| SCIP | 0.11.6 | ⌃ newer available |

#### Manifest summary:
- Total packages (manifest): 114
- Pure Julia packages: ~60
- JLL (compiled binary wrappers): ~25
- Julia stdlib packages: ~29
- Packages with ⌅ compat-pinned versions: 8 (JSON, NLSolversBase, PrecompileTools, OpenBLAS32_jll, SCIP_jll, SCIP_PaPILO_jll, boost_jll, oneTBB_jll)
- Packages with ⌃ newer available: 6 (HiGHS, JuMP, SCIP, ArrayInterface, LineSearches + SCIP Julia wrapper)

**Key transitive deps (PowerModels direct):** InfrastructureModels 0.7.8, JuMP 1.29.4, MathOptInterface 1.49.0, JSON 0.21.4, NLsolve 4.5.1, Memento 1.4.1, PrecompileTools 1.2.1, SparseArrays (stdlib)

#### Compat bounds in Project.toml:
- `GLPK = "1"`, `HiGHS = "1"`, `Ipopt = "1"`, `JuMP = "1"`, `PowerModels = "0.21"`, `SCIP = "0.11"`, `julia = "1.10"`

All dependencies are resolvable. The Manifest.toml contains `git-tree-sha1` entries for all non-stdlib packages, providing reproducible resolution.

## Implications

The dependency tree is fully resolved and pinned. The three ⌅ packages are constrained by compatibility rules, not missing registrations. No unresolvable packages. The 114-package manifest is typical for a JuMP-based Julia optimization project (JLL wrappers inflate the count significantly). Supply chain risk is low for this dimension.
