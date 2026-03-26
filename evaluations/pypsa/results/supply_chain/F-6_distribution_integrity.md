---
test_id: F-6
tool: pypsa
dimension: supply_chain
network: N/A
protocol_version: v11
skill_version: v2
test_hash: e598e441
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
loc: null
solver: null
timestamp: 2026-03-24T14:00:00Z
---

# F-6: Distribution Integrity

## Result: PASS

## Finding

PyPSA is distributed via PyPI (standard Python package repository) with versioned releases, SHA-256/BLAKE2b digest hashes, and automated CI/CD release pipeline. No PGP signatures (deprecated by PyPI in 2023), no Sigstore attestations yet.

## Evidence

### Distribution Channel

- **Primary**: PyPI — https://pypi.org/project/pypsa/
- **Source**: GitHub — https://github.com/PyPSA/PyPSA

### Versioned Releases

All releases use semantic versioning. PyPI release history shows 50+ versioned releases. Current version: v1.1.2.

### Release Artifacts (v1.1.2)

| Artifact | Type | Platform |
|----------|------|----------|
| `pypsa-1.1.2-py3-none-any.whl` | Wheel | Platform-independent (pure Python) |
| `pypsa-1.1.2.tar.gz` | Source distribution | Platform-independent |

Both artifacts include SHA-256, MD5, and BLAKE2b-256 digest hashes provided by PyPI infrastructure.

### Signing Status

- **PGP signatures**: No (`has_sig: false`). PyPI deprecated PGP signature uploads in 2023.
- **Sigstore attestations**: Not yet adopted. This is a gap shared across most of the Python ecosystem.
- **Trusted Publishers**: The release workflow uses GitHub Actions, which enables PyPI Trusted Publishers (OIDC-based provenance).

### Release Process

- `release.yml` GitHub Actions workflow automates build and PyPI upload
- Version derived from git tags via `setuptools_scm`
- Git tags match PyPI versions (e.g., `v1.1.2`)

### Flags

- No unversioned tarballs or blob store artifacts
- No mutable download URLs
- Standard PyPI distribution channel with hash verification

## Implications

Distribution integrity is solid. The lack of Sigstore attestations is an ecosystem-wide gap, not specific to PyPSA. PyPI's hash-based integrity plus Trusted Publishers OIDC provenance provides reasonable supply chain assurance.
