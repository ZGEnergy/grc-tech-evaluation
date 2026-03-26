---
test_id: F-6
tool: gridcal
dimension: supply_chain
network: N/A
status: pass
workaround_class: null
protocol_version: "v11"
skill_version: v2
test_hash: "9d3540a1"
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: null
solver: null
timestamp: "2026-03-24T18:00:00Z"
---

# F-6: Distribution Integrity

## Result: PASS

## Finding

VeraGridEngine is distributed via PyPI as a source distribution (sdist) only -- no pre-built wheels. Releases are versioned (SemVer-like) but not cryptographically signed. SHA-256 digests are available via PyPI's JSON API. The project uses a single-maintainer publishing workflow with no Trusted Publisher (OIDC) configuration.

## Evidence

**Distribution format:**
- Package type: `sdist` (.tar.gz) -- no wheel distributions published
- Pure Python (`py3-none-any`), so sdist-only distribution is acceptable (no compilation required)
- Latest PyPI version: 5.6.38 (as of 2026-03-24); installed version: 5.6.28

**Integrity verification:**
- SHA-256 and MD5 digests available via PyPI JSON API for every release
- `has_sig: False` on all examined releases -- no PGP/GPG signatures
- No Sigstore/cosign signatures
- No SBOM (Software Bill of Materials) published

**Release process:**
- Published by a single account (Santiago Penate Vera / spenate@eroots.tech)
- No GitHub Actions Trusted Publisher (OIDC) workflow detected
- Releases appear manually published from developer's local machine
- 70 total releases on PyPI for `veragridengine`

**Versioning:**
- SemVer-like: `MAJOR.MINOR.PATCH` (e.g., 5.6.28)
- Version string queryable via `importlib.metadata.version('veragridengine')`

**GitHub-PyPI alignment:**
- GitHub releases: 5 tagged releases found (5.6.20, v5.4.0, v5.3.0, v5.2.0, v5.1.20)
- Most PyPI releases lack corresponding GitHub tags or release notes
- This makes it difficult to correlate a PyPI version with a specific source tree state

**GitHub repository:**
- Repo: SanPen/VeraGrid (519 stars, 124 forks as of 2026-03-24)
- Created: 2016-01-13
- Default branch: master
- 28 open issues

## Implications

The distribution integrity profile has gaps typical of a single-developer open-source project: no release signing, no Trusted Publisher workflow, single-account publishing, and incomplete GitHub-PyPI version alignment. The sdist-only distribution is a minor positive for inspectability (no pre-compiled binaries shipped). The lack of signing means integrity verification relies solely on PyPI's hash verification, which protects against transit corruption but not supply chain compromise of the publishing credentials.
