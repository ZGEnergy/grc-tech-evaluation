---
test_id: F-6
tool: powermodels
dimension: supply_chain
network: N/A
status: pass
workaround_class: null
timestamp: "2026-03-13T23:00:00Z"
protocol_version: v10
skill_version: v1
test_hash: "34d044d2"
---

# F-6: Release distribution channel and integrity

## Finding

PowerModels.jl is distributed exclusively through the Julia General Registry with versioned, content-hash-verified releases. Every version entry in the registry includes a `git-tree-sha1` hash that Julia's package manager verifies on download. No unversioned tarballs or mutable download links are used in the distribution channel.

## Evidence

### Distribution channel

Julia General Registry (`https://github.com/JuliaRegistries/General`). This is the sole official distribution channel for PowerModels.jl. The package is not distributed via ad-hoc tarballs, blob storage, or any other mutable URL.

### Versioning

Semantic versioning enforced. Current version: 0.21.5. Every release is tagged on GitHub at `https://github.com/lanl-ansi/PowerModels.jl`.

Registry entry for PowerModels 0.21.5 confirms:
```
git-tree-sha1 = "b8e410e1d827b621e82e7e670967f0efc5845c30"
```

Manifest.toml in the evaluation environment matches:
```
[[deps.PowerModels]]
git-tree-sha1 = "b8e410e1d827b621e82e7e670967f0efc5845c30"
uuid = "c36e90e8-916a-50a6-bd94-075b64ef4655"
version = "0.21.5"
```

### Integrity mechanism

- Julia's `Pkg.resolve()` downloads packages from GitHub source archives and verifies the `git-tree-sha1` from the registry. A mismatch causes install failure.
- All JLL binary artifacts include SHA-256 checksums in their `Artifacts.toml` files, verified by Julia's artifact system on download.
- The `project_hash` in `Manifest.toml` (`3fee691dbfc6cebc34fe42292e050c55b3373e6f`) captures the resolved state of the entire dependency graph.

### Signing

Julia packages are not GPG-signed at the package level (not standard practice in the Julia ecosystem). Integrity is assured by SHA-based content hashing in the registry, which provides tamper detection through content-addressable verification.

### No unversioned artifacts

No `@main`, `@dev`, or unversioned branch references exist in the Manifest.toml. All 100+ packages are pinned to specific versions with git-tree-sha1 hashes.

## Implications

Distribution integrity is strong. The git-tree-sha1 content-addressable hash in the registry provides tamper detection equivalent to signed releases for practical purposes. All dependencies are versioned and pinned in the Manifest.toml. No risk of silent dependency mutation exists in the installed configuration.
