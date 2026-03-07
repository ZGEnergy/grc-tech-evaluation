---
test_id: F-6
tool: powersimulations
dimension: supply_chain
network: N/A
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: null
peak_memory_mb: null
loc: null
solver: null
timestamp: "2026-03-07T05:00:00Z"
---

# F-6: Distribution Integrity

## Method

Examined how PowerSimulations.jl and its dependencies are released and distributed.

## Findings

### Distribution Channel

All Julia packages (including PowerSimulations.jl) are distributed via the **Julia General Registry**, a public Git repository at `github.com/JuliaRegistries/General`. This is the standard and only mainstream distribution channel for Julia packages.

### Versioned Releases

PowerSimulations.jl uses semantic versioning with regular tagged releases:

| Version | Date |
|---------|------|
| v0.33.1 | 2026-02-24 |
| v0.33.0 | 2026-02-18 |
| v0.32.4 | 2025-12-18 |
| v0.32.3 | 2025-12-13 |
| v0.32.2 | 2025-12-10 |

Active development with regular releases.

### Content Addressing

Julia's package manager uses **content-addressed** storage:
- Every package version is identified by a `git-tree-sha1` hash (the SHA-1 of the git tree object for that version's source)
- These hashes are recorded in the General Registry and in the project's `Manifest.toml`
- The Manifest.toml contains 135 `git-tree-sha1` entries for non-stdlib packages
- Artifact binaries (JLL packages) use SHA-256 content hashes

### Signed Artifacts

- **Git tags:** GitHub releases are created from git tags. Not GPG-signed by default.
- **Registry entries:** The General Registry uses automated registration bots (JuliaRegistrator). Registry PRs are reviewed by the bot and auto-merged. No cryptographic signing of registry entries.
- **Binary artifacts:** JLL artifacts use SHA-256 content hashes for integrity verification but are not cryptographically signed.

### Reproducibility

The `Manifest.toml` lockfile ensures fully reproducible installs. Every dependency is pinned to an exact version and content hash. Running `Pkg.instantiate()` with a given Manifest.toml will always produce the same environment.

## Assessment

Releases are versioned, content-addressed, and distributed through the standard Julia General Registry. No unversioned tarballs or mutable URLs. The only gap versus ideal is the lack of cryptographic signatures on registry entries and artifacts, which is standard for the Julia ecosystem (and comparable to PyPI before Sigstore adoption). **Pass.**
