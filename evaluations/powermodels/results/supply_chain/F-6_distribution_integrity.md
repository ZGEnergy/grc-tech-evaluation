---
test_id: F-6
tool: powermodels
dimension: supply_chain
status: qualified_pass
timestamp: 2026-03-05
---

# F-6: Distribution Integrity

## Finding

PowerModels.jl is distributed through the Julia General Registry, which provides version-pinned, content-hashed distribution but lacks cryptographic signing. Packages are registered via automated PR review (RegistryCI) against the General registry Git repository.

## Evidence

**Distribution channel**: Julia General Registry (<https://github.com/JuliaRegistries/General>)

**Version pinning**: The `Manifest.toml` file pins exact versions and includes tree hashes (SHA-1 of the package source tree):

```toml
[deps.PowerModels]
uuid = "c36e90e8-916a-50a6-bd94-075b64ef4655"
version = "0.21.5"

```

**Integrity mechanisms**:
- **Tree hashes**: Each package version in the registry includes a `git-tree-sha1` hash computed from the package source tree, providing content integrity verification.
- **Registry CI**: Automated CI checks (RegistryCI.jl) validate registry consistency on every PR. Checks include version number validation, dependency compatibility, and naming conventions.
- **TagBot**: Automated release tagging ensures registry entries correspond to GitHub tags.
- **Automerge**: Qualifying PRs are auto-merged after CI passes and a waiting period.

**What is NOT present**:
- No GPG/cryptographic signing of packages or registry entries
- No signature verification during `Pkg.add()`
- No SBOM (Software Bill of Materials) generation
- No attestation or provenance metadata (unlike npm provenance or Python's PEP 740)

**JLL binary integrity**: JLL packages are built via Yggdrasil CI and hosted on GitHub Releases as tarballs. These have content hashes but no independent signing.

Source: <https://github.com/JuliaRegistries/General,> <https://julialang.github.io/Pkg.jl/v1/registries/>

## Implications

The Julia package ecosystem provides content-hash-based integrity (preventing accidental corruption) but lacks cryptographic signing (which would prevent targeted supply chain attacks). This is comparable to pip/PyPI before PEP 740 adoption. The tree-hash system is stronger than no verification but weaker than signed packages. For a government/critical-infrastructure context, the lack of signing is a notable gap. Qualified pass because content hashes provide meaningful integrity while acknowledging the signing gap.
