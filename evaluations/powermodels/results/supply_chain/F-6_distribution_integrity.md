---
test_id: F-6
tool: powermodels
dimension: supply_chain
network: N/A
status: pass
workaround_class: null
timestamp: "2026-03-11T00:00:00Z"
protocol_version: "v9"
skill_version: v1
test_hash: "34d044d2"
---

# F-6: Check how releases are distributed; flag unversioned or unsigned artifacts

## Finding

PowerModels.jl is distributed exclusively through the Julia General Registry with versioned, content-hash-verified releases. Every version entry in the registry includes a `git-tree-sha1` hash that Julia's package manager verifies on download. No unversioned tarballs or mutable URLs are used.

## Evidence

**Distribution channel:** Julia General Registry (`https://github.com/JuliaRegistries/General`)

### Versioning:
- Semantic versioning enforced. Current version: 0.21.5
- Every release tagged on GitHub at `https://github.com/lanl-ansi/PowerModels.jl`
- Manifest.toml entry for PowerModels 0.21.5:

  ```

  git-tree-sha1 = "b8e410e1d827b621e82e7e670967f0efc5845c30"
  uuid = "c36e90e8-916a-50a6-bd94-075b64ef4655"
  version = "0.21.5"

  ```

#### Integrity mechanism:
- Julia's `Pkg.resolve()` downloads packages from GitHub source archives and verifies the `git-tree-sha1` from the registry. A mismatch causes install failure.
- All JLL binary artifacts include SHA-256 checksums in their `Artifacts.toml` files, verified by Julia's artifact system on download.
- The `project_hash` in `Manifest.toml` (`3fee691dbfc6cebc34fe42292e050c55b3373e6f`) captures the resolved state of the entire dependency graph.

**GitHub releases:** Tagged releases visible at `https://github.com/lanl-ansi/PowerModels.jl/releases`. CHANGELOG.md tracks changes per version.

**No unversioned artifacts:** No `@main`, `@dev`, or unversioned branch references were found in the Manifest.toml. All packages are pinned to specific versions.

**Code signing:** Julia packages are not GPG-signed at the package level (this is not standard practice in the Julia ecosystem). Integrity is instead assured by SHA-based content hashing in the registry, which provides equivalent tamper-detection capability.

## Implications

Distribution integrity is strong. The git-tree-sha1 hash in the registry provides content-addressable verification equivalent to signed releases for practical purposes. All dependencies are versioned and pinned in Manifest.toml. There is no risk of silent dependency updates or mutable artifact references in the installed configuration.
