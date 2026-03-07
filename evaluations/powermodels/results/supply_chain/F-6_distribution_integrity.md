---
test_id: F-6
tool: powermodels
dimension: supply_chain
network: N/A
protocol_version: "v4"
status: pass
workaround_class: null
timestamp: 2026-03-06T00:00:00Z
---

# F-6: Distribution Integrity

## Result: PASS

## Finding

PowerModels.jl is distributed via the Julia General Registry with versioned releases, content-addressed artifact hashes, and a deterministic lockfile (Manifest.toml). The distribution channel is the standard Julia package ecosystem with reproducible resolution.

## Evidence

**Distribution channel**: Julia General Registry (<https://github.com/JuliaRegistries/General>). This is the official, community-maintained package registry for Julia, analogous to PyPI or npm.

**Version management**:
- PowerModels v0.21.5 is a tagged release
- Manifest.toml entry: `git-tree-sha1 = "b8e410e1d827b621e82e7e670967f0efc5845c30"`, `uuid = "c36e90e8-916a-50a6-bd94-075b64ef4655"`
- The `git-tree-sha1` is a content-addressable hash of the package tree, ensuring integrity

**Lockfile**: The `Manifest.toml` (format v2.0, generated for Julia 1.10.10) records exact versions and tree hashes for all 114 dependencies. This provides full reproducibility: `Pkg.instantiate()` on a given Manifest.toml will install identical code.

**Project hash**: `project_hash = "3fee691dbfc6cebc34fe42292e050c55b3373e6f"` in Manifest.toml header ensures manifest-project consistency.

**Signing**: Julia packages are not cryptographically signed (GPG or similar). Integrity relies on content-addressed hashes (git tree SHA1) rather than signatures. This is a known limitation of the Julia ecosystem but is consistent with most language package managers (pip, npm).

**Source repository**: <https://github.com/lanl-ansi/PowerModels.jl> under the LANL-ANSI GitHub organization. Releases correspond to git tags.

**Compat bounds in PowerModels/Project.toml**:

```

InfrastructureModels = "0.6, 0.7"
JSON = "0.21"
JuMP = "1.15"
Memento = "1"
NLsolve = "4"
PrecompileTools = "1"
julia = "1.6"

```

## Implications

The distribution model is sound. Content-addressed hashes ensure tamper detection. The Manifest.toml lockfile enables reproducible deployments. The lack of cryptographic signatures is a minor gap shared with most language ecosystems and does not materially degrade supply chain integrity for this use case.
