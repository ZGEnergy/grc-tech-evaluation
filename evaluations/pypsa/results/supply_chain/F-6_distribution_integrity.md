---
test_id: F-6
tool: pypsa
dimension: supply_chain
network: N/A
status: pass
workaround_class: null
timestamp: 2026-03-13T12:00:00Z
protocol_version: v10
skill_version: v1
test_hash: e598e441
---

# F-6: Distribution Integrity

## Findings

### Distribution Channel

**PyPI** (Python Package Index) — the standard Python package repository.

- Package URL: https://pypi.org/project/pypsa/
- Source URL: https://github.com/PyPSA/PyPSA

### Versioned Releases

**Yes.** All releases are versioned using semantic versioning. The PyPI
release history shows 50+ versioned releases going back to the initial
PyPI upload.

### Release Artifacts

For v1.1.2 (current):
- `pypsa-1.1.2-py3-none-any.whl` — Python wheel (pure Python, platform-independent)
- `pypsa-1.1.2.tar.gz` — Source distribution

Both artifacts include SHA-256, MD5, and BLAKE2b-256 digest hashes
provided by PyPI's infrastructure.

### Signed Artifacts

**No.** PyPI indicates `has_sig: false` for both the wheel and source
distribution. PGP signatures are not provided.

This is typical for the Python ecosystem — PyPI deprecated PGP signature
support in 2023 in favor of Trusted Publishers and Sigstore-based
attestations. PyPSA's release workflow (`release.yml`) uses GitHub Actions,
which enables PyPI Trusted Publishers but does not currently produce
Sigstore attestations.

### Release Process

The GitHub repository has a `release.yml` workflow that automates:
1. Package build via `setuptools_scm` (version from git tags)
2. Upload to PyPI

Releases are tagged in git with the version number (e.g., `v1.1.2`).

### Flags

- No unversioned tarballs or blob store artifacts
- No mutable download URLs
- Standard PyPI distribution channel

## Recorded Metrics

- versioned: yes (semantic versioning)
- signed: no (PGP deprecated on PyPI; no Sigstore attestations)
- channel: PyPI (standard)
- flags: none
