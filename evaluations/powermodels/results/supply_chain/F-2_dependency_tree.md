---
test_id: F-2
tool: powermodels
dimension: supply_chain
network: N/A
status: pass
workaround_class: null
timestamp: "2026-03-13T23:01:54Z"
protocol_version: v10
skill_version: v1
test_hash: "090796da"
---

# F-2: Full dependency tree enumeration

## Finding

The resolved manifest contains 114 packages total (6 direct, 108 transitive including stdlib). All direct dependencies are pinned by the Manifest.toml with exact versions and git-tree-sha1 hashes. Three packages have newer versions available (marked with caution) but are not upgradable within current compat bounds. No unresolvable dependencies were detected.

## Evidence

Command: `.devcontainer/dc-exec -C /workspace/evaluations/powermodels julia --project=. -e 'using Pkg; Pkg.status()'`

### Direct dependencies (from Project.toml):

| Package | Version | Compat Bound | Status |
|---------|---------|--------------|--------|
| GLPK | 1.2.1 | "1" | pinned |
| HiGHS | 1.21.1 | "1" | newer available |
| Ipopt | 1.14.1 | "1" | pinned |
| JuMP | 1.29.4 | "1" | newer available |
| PowerModels | 0.21.5 | "0.21" | pinned |
| SCIP | 0.11.6 | "0.11" | newer available |

### Manifest breakdown:

| Category | Count |
|----------|-------|
| Total packages | 114 |
| Direct dependencies | 6 |
| Pure Julia (transitive) | ~50 |
| JLL binary wrappers | 35 |
| Julia stdlib packages | ~23 |

### Key transitive dependencies:

- InfrastructureModels 0.7.8 (PowerModels' infrastructure layer)
- JuMP 1.29.4 / MathOptInterface 1.49.0 (optimization modeling)
- JSON 0.21.4, NLsolve 4.5.1, Memento 1.4.1 (utilities)
- ForwardDiff 1.3.2 (automatic differentiation for NLP)

### Tree depth:

The deepest chain is approximately: PowerModels -> JuMP -> MathOptInterface -> solver JLL -> compiler support libs (5 levels). The JLL binary wrapper layer adds significant breadth (35 packages) but minimal depth.

All dependencies are resolvable. The Manifest.toml contains `git-tree-sha1` entries for all non-stdlib packages, providing reproducible resolution. Julia version pinned to 1.10+.

## Implications

The dependency tree is fully resolved and pinned. The 114-package manifest is typical for a JuMP-based Julia optimization project (JLL wrappers inflate the count significantly but are standard infrastructure). No unresolvable or missing packages. Supply chain risk is low for this dimension.
