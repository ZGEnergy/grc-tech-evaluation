---
test_id: F-6
tool: pandapower
dimension: supply_chain
network: N/A
status: informational
workaround_class: null
timestamp: 2026-03-13T00:00:00Z
protocol_version: v11
skill_version: v2
test_hash: "3d597872"
---

# F-6: Distribution Integrity

## Summary

pandapower is distributed through PyPI with Sigstore provenance attestations, semantic
versioning, and immutable release artifacts. **Grade: A.**

## Findings

### Distribution Channel

pandapower is published to PyPI as the canonical distribution channel. The current
version is 3.4.0 (released 2026-02-09). Both source distribution (`.tar.gz`, 5.2 MB)
and built distribution (`.whl`, 5.5 MB) are provided as a pure-Python
`py3-none-any` wheel.

### Versioning

The project uses semantic versioning (MAJOR.MINOR.PATCH). GitHub releases are tagged
(e.g., `v3.4.0`, `v3.3.3`, `v3.2.0`) with corresponding changelogs. A `CHANGELOG.rst`
is maintained in the repository.

### Signing and Provenance

- **Sigstore provenance attestations** are present on both distribution files. Each
  artifact has an in-toto attestation statement and a Sigstore transparency log entry
  (entries 930486146 and 930486147).
- Artifacts are published via GitHub Actions using the `upload_release.yml` workflow
  through PyPI Trusted Publishing (twine 6.1.0).
- **No traditional GPG `.asc` signatures** are provided, but Sigstore attestations are
  the modern replacement and are considered equivalent or superior.
- SHA256 and BLAKE2b-256 hashes are published on PyPI for each artifact.

### Immutability

PyPI artifacts are immutable once published — a given version cannot be overwritten.
No mutable download links (e.g., direct tarballs from `develop` branch) are used as
the primary distribution mechanism.

## Risks

None identified. The distribution pipeline follows current best practices with
Trusted Publishing and Sigstore provenance.
