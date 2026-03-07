---
test_id: F-6
tool: pandapower
dimension: supply_chain
network: N/A
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: null
peak_memory_mb: null
loc: null
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# F-6: Distribution Integrity

## Result: PASS

## Finding

pandapower is distributed via PyPI with versioned releases, both sdist and wheel formats,
and Sigstore attestation bundles generated via GitHub Actions Trusted Publishing. The
release process is automated and cryptographically verifiable.

## Evidence

### Distribution channel

- **Primary:** [PyPI](https://pypi.org/project/pandapower/) -- `pip install pandapower`
- **Source:** [GitHub](https://github.com/e2nIEE/pandapower) -- `e2nIEE/pandapower`

### Release artifacts (v3.4.0)

| Artifact | Size | Format |
|----------|------|--------|
| `pandapower-3.4.0.tar.gz` | 5.2 MB | sdist |
| `pandapower-3.4.0-py3-none-any.whl` | 5.5 MB | wheel |

### Versioning

- Follows semantic versioning (MAJOR.MINOR.PATCH).
- ~58 releases on PyPI from v1.1.1 (Jan 2017) through v3.4.0 (Feb 9, 2026).
- Each release has a corresponding GitHub release tag.

### Signing and attestation

- **Trusted Publishing:** Yes -- releases are published via GitHub Actions workflow
  (`upload_release.yml`).
- **Sigstore attestations:** Both sdist and wheel have Sigstore transparency log entries
  (entries 930486146 and 930486147 for v3.4.0).
- **Provenance:** Attestation bundles link the published artifacts to the GitHub Actions
  workflow run that produced them, establishing a verifiable build chain.

### Reproducibility

- The `py3-none-any` wheel format means no platform-specific compilation at install time.
- The sdist allows building from source.
- Dependencies are pinned with compatible-release operators (`~=`) in `pyproject.toml`.

## Implications

pandapower follows modern Python packaging best practices. The combination of PyPI
distribution, Sigstore attestation via Trusted Publishing, and versioned releases with
both sdist and wheel formats provides strong distribution integrity guarantees. The
cryptographic attestation chain from GitHub source to PyPI artifact is a significant
positive signal for supply chain security.
