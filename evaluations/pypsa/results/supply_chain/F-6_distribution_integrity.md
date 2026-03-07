---
test_id: F-6
tool: pypsa
dimension: supply_chain
slug: distribution_integrity
network: N/A
protocol_version: v4
status: pass
workaround_class: null
timestamp: 2026-03-06T12:00:00Z
---

# F-6: Distribution Integrity Audit

## Distribution Channel

PyPSA is distributed via **PyPI** (<https://pypi.org/project/pypsa/>) and **conda-forge**.

## Release Artifacts (v1.1.2)

| Artifact | Size | Type |
|----------|------|------|
| `pypsa-1.1.2.tar.gz` | 13.0 MB | Source distribution (sdist) |
| `pypsa-1.1.2-py3-none-any.whl` | 347.3 kB | Pure-Python wheel |

The wheel is `py3-none-any`, confirming PyPSA contains no compiled extensions and is platform-independent.

## Versioning

PyPSA uses **semantic versioning (SemVer)**. Recent version progression:

```
v0.30.0 -> v0.30.1 -> v0.30.2 -> v0.30.3
v0.31.0 -> v0.31.1 -> v0.31.2
v0.32.0 -> v0.32.1 -> v0.32.2
v0.33.0 -> v0.33.1 -> v0.33.2
v0.34.0 -> v0.34.1
v0.35.0 -> v0.35.1 -> v0.35.2
v1.0.0rc1 -> v1.0.0 -> v1.0.1 -> v1.0.2 -> v1.0.3 -> v1.0.4 -> v1.0.5 -> v1.0.6 -> v1.0.7
v1.1.0 -> v1.1.1 -> v1.1.2
```

SemVer is strictly followed. The v1.0.0 milestone included a release candidate (v1.0.0rc1).

## Cryptographic Signing

- **Sigstore attestations**: Both sdist and wheel include Sigstore transparency log entries (in-toto Statement v1 format with PyPI publish predicate)
  - sdist: transparency entry #983350354
  - wheel: transparency entry #983350377
- **Publishing mechanism**: Trusted Publishing via GitHub Actions (no manual uploads)
- **PGP signatures**: Not used (Sigstore is the modern replacement on PyPI)

## Maintainers

Three maintainers with PyPI upload access:
- `fneum` (Fabian Neumann)
- `lkstrp` (Lukas Strippe)
- `nworbmot` (Tom Brown)

## Assessment

**PASS** -- PyPSA is distributed through standard, trusted channels (PyPI, conda-forge) with Sigstore cryptographic attestations. Releases follow strict SemVer. Publishing is automated via GitHub Actions trusted publishing, reducing the risk of supply chain attacks through compromised maintainer credentials. The pure-Python wheel minimizes platform-specific supply chain risk.
