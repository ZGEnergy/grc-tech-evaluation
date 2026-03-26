---
test_id: F-6
tool: powersimulations
dimension: supply_chain
network: N/A
protocol_version: "v11"
skill_version: "v2"
test_hash: "34d044d2"
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
solver: null
timestamp: 2026-03-24T00:00:00Z
---

# F-6: Distribution Integrity

## Result: INFORMATIONAL

## Summary

PowerSimulations.jl is distributed via Julia's General Registry with git-tree-SHA1
content hashes for every version. Binary dependencies (JLL packages) include SHA-256
hashes on all download artifacts. The distribution chain provides strong integrity
verification, though it does not use cryptographic signatures (GPG/Sigstore).

## Distribution Channel

### Julia General Registry

All packages are registered in the [Julia General Registry](https://github.com/JuliaRegistries/General),
a public GitHub repository maintained by the Julia community.

- **Registry URL:** `https://github.com/JuliaRegistries/General`
- **Registration:** Each package version has an entry in `Versions.toml` with a
  `git-tree-sha1` content hash
- **Automated registration:** Via JuliaRegistrator bot on GitHub (requires package
  maintainer to trigger)

### PowerSimulations.jl Versions (recent)

| Version | git-tree-sha1 | Date |
|---------|---------------|------|
| 0.33.1 | `d918230822ce9cfbbca2fcebf1ee980385ef2c73` | 2026-02-24 |
| 0.33.0 | `c745152ab3fc5b1d2296fe977725eb0c0cf95de4` | 2026-02-18 |
| 0.32.4 | `11df940a679209621b8848df49ead18cc607e925` | 2025-12-18 |
| 0.30.2 | (in Manifest.toml) | 2025-06-09 |

### Versioning Scheme

- **Semantic versioning** (semver): `MAJOR.MINOR.PATCH`
- **Pre-1.0:** No API stability guarantees (currently v0.33.x)
- **21 releases in the last 24 months** with regular cadence

## Integrity Verification Mechanisms

### 1. Git Tree SHA-1 (Julia packages)

Every registered package version is identified by its `git-tree-sha1`, which is a
content-addressable hash of the entire source tree. Julia's package manager (`Pkg`)
verifies this hash when downloading package source.

- **Hash algorithm:** SHA-1 (git tree hash)
- **Verification:** Automatic on `Pkg.add()` / `Pkg.instantiate()`
- **Tampering detection:** Any modification to package source changes the tree hash

### 2. SHA-256 Artifact Hashes (JLL binary packages)

JLL packages include `Artifacts.toml` files with SHA-256 hashes for every binary
artifact. Example from HiGHS_jll:

```
[HiGHS] (Linux x86_64)
git-tree-sha1 = "57846bf52e8d91e2d6dfef3b0e474315208dc524"
download url = https://github.com/JuliaBinaryWrappers/.../HiGHS.v1.13.1.x86_64-linux-gnu-cxx11.tar.gz
download sha256 = "3bf8ba4b53be90f8a36d6ad12fdb09ab6ebe572aaa3ea405509daf7c2e10d7fb"
```

- **Hash algorithm:** SHA-256
- **Verification:** Automatic on artifact download
- **Coverage:** All solver JLLs (HiGHS, GLPK, Ipopt, SCIP) and all transitive
  binary dependencies (41 JLL packages total)

### 3. Manifest.toml Lock File

The `Manifest.toml` records exact resolved versions and git-tree-sha1 for every
dependency. This provides a reproducible dependency snapshot.

- **184 packages** locked in our evaluation Manifest
- **Exact version pins** for every transitive dependency
- **Reproducible installs** via `Pkg.instantiate()` from the lock file

## What Is NOT Provided

| Mechanism | Status |
|-----------|--------|
| GPG/PGP signatures on packages | Not available |
| Sigstore/cosign signatures | Not available |
| SBOM (Software Bill of Materials) | Not generated automatically |
| Reproducible builds (bit-for-bit) | JLL builds are reproducible via Yggdrasil, but not formally attested |
| Code signing on binaries | Not available |
| Two-party review on registry | Automated via JuliaRegistrator; registry PRs are auto-merged after checks pass |

## Supply Chain Attack Surface

### Registry Compromise

The General Registry is a GitHub repository. A compromise of the registry could
redirect package downloads. Mitigations:
- Registry PRs are reviewed by automated checks (RegistryCI)
- Tree hashes provide content verification
- The registry itself is widely monitored by the Julia community

### JLL Binary Compromise

JLL binaries are hosted on GitHub Releases for the JuliaBinaryWrappers organization.
A compromise of these releases could inject malicious binaries. Mitigations:
- SHA-256 hashes in Artifacts.toml detect tampering after initial registration
- Build recipes in Yggdrasil are public and auditable
- Artifacts can be rebuilt from Yggdrasil recipes for verification

### Package Source Compromise

A compromise of the NREL-Sienna GitHub organization could inject malicious code
into a new release. Mitigations:
- New versions require explicit registration via JuliaRegistrator
- Existing Manifest.toml pins are not affected by new releases
- Code review is part of the NREL-Sienna development workflow

## Assessment

The distribution integrity is **adequate for most deployment scenarios**. SHA-256
hashes on binary artifacts and git-tree-sha1 on source packages provide tamper
detection. The absence of cryptographic signatures (GPG/Sigstore) is a gap
compared to ecosystems like Python (PEP 740) or Rust (crates.io transparency log),
but is standard for the Julia ecosystem. The Manifest.toml lock file provides
reproducible installs from verified content hashes.

## Data Source

- Julia General Registry `Versions.toml` for PowerSimulations.jl (accessed 2026-03-24)
- Manifest.toml in evaluation project (accessed 2026-03-24)
- HiGHS_jll Artifacts.toml SHA-256 hashes (accessed 2026-03-24)
