---
test_id: F-6
tool: matpower
dimension: supply_chain
network: N/A
protocol_version: "v11"
skill_version: v2
test_hash: 647d2472
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
solver: null
timestamp: 2026-03-14T00:00:00Z
---

# F-6: Distribution Integrity

## Result: PASS

## Finding

MATPOWER uses versioned GitHub releases with SHA-256 checksums as the primary distribution channel. Zenodo DOIs provide archival persistence. Releases are versioned tarballs/zip files with consistent naming conventions.

## Evidence

**GitHub releases (last 6 releases, accessed 2026-03-14):**

| Version | Date | Type |
|---------|------|------|
| 8.1 | 2025-07-13 | Latest |
| 8.0 | 2024-05-17 | Stable |
| 8.0b1 | 2022-12-23 | Pre-release |
| 7.1 | 2020-10-08 | Stable |
| 7.0 | 2019-06-21 | Stable |
| 7.0b1 | 2018-11-01 | Pre-release |

**Release artifact for v8.1:**
- File: `matpower8.1.zip` (47.3 MB)
- SHA-256: `7f13b1441669a64e312d14a60e564cd91977ff1676ff77d25538e94ff313dd56`
- Download count: 89,498 (as of 2026-03-14)
- GitHub asset digest field confirms SHA-256 checksum

**Distribution channels:**
1. **GitHub Releases:** Primary channel. Versioned zip artifacts with checksums. URL pattern: `https://github.com/MATPOWER/matpower/releases/download/{version}/matpower{version}.zip`
2. **matpower.org:** Project website with download links (points to GitHub)
3. **Zenodo:** Archival DOIs for long-term persistence (DOI: 10.5281/zenodo.3236535 for the concept record)

**Integrity verification:**
The project's own `setup.sh` demonstrates checksum verification:
```bash
echo "${MATPOWER_SHA256}  matpower${MATPOWER_VERSION}.zip" | sha256sum -c -
```

**Signed artifacts:** GitHub releases do not include GPG signatures, but the SHA-256 digest is provided via GitHub's asset metadata API. The checksum in `setup.sh` was verified to match the GitHub-reported digest.

## Implications

Distribution integrity is strong. Versioned releases with SHA-256 checksums provide tamper detection. The Zenodo archive provides long-term availability independent of GitHub. The lack of GPG signatures is a minor gap but mitigated by the GitHub-hosted checksums and the Zenodo DOI system.
