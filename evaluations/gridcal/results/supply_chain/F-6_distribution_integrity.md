---
test_id: F-6
tool: gridcal
dimension: supply_chain
network: N/A
status: informational
workaround_class: null
protocol_version: "v10"
skill_version: v1
test_hash: "9d3540a1"
timestamp: "2026-03-13T23:00:00Z"
---

# F-6: Distribution Integrity

## Finding

VeraGridEngine is distributed via PyPI as a source distribution (sdist) only — no pre-built wheels. Releases are not cryptographically signed (PGP). SHA-256 digests are available via PyPI's API. No Trusted Publisher (OIDC) workflow is configured.

## Evidence

**Distribution format:**
- Package type: `sdist` (source distribution, `.tar.gz`)
- No wheel (`.whl`) distributions published
- This means every `pip install` requires building from source, which is acceptable since VeraGridEngine is pure Python

**Signing and verification:**
- `has_sig: False` on all PyPI releases examined
- No PGP/GPG signatures on releases
- No Sigstore/cosign signatures
- SHA-256 digest available: `5a036d1ec369f677e8f8...` (for 5.6.28)
- PyPI provides SHA-256 and MD5 hashes via its JSON API for integrity verification

**Release process:**
- Published by a single account (`spenate@eroots.tech`)
- No GitHub Actions publishing workflow (no Trusted Publisher OIDC)
- Releases appear to be manually published from the developer's local machine
- No SBOM (Software Bill of Materials) published with releases

**Versioning:**
- SemVer-like: `MAJOR.MINOR.PATCH`
- No pre-release suffixes on `veragridengine` releases (though `gridcalengine` had beta tags)
- Version string is embedded in the package and queryable via `importlib.metadata.version('veragridengine')`

**GitHub-PyPI alignment:**
- Only 28 of 66 `veragridengine` releases have corresponding GitHub tags
- Most releases are published to PyPI without a GitHub tag or release note
- This makes it difficult to correlate a PyPI version with a specific source tree state

## Implications

The distribution integrity profile has several gaps: no release signing, no Trusted Publisher workflow, single-account publishing, and poor GitHub-PyPI version alignment. The manual publishing process from a single developer's machine introduces a supply chain risk — compromise of that developer's PyPI credentials would allow malicious releases. The sdist-only distribution is actually a minor positive for inspectability (no pre-compiled binaries), but the lack of signing means there is no cryptographic guarantee that a PyPI download matches the developer's intended release.
