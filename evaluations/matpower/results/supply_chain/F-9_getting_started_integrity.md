---
test_id: F-9
tool: matpower
dimension: supply_chain
network: N/A
protocol_version: v10
skill_version: v1
test_hash: 71a3d59e
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

# F-9: Getting Started Integrity

## Result: PASS

## Finding

MATPOWER's getting-started workflow uses version-pinned, checksummed distribution artifacts from stable URLs. The download URL pattern includes the version number, and the GitHub release system provides immutable, versioned artifacts. No mutable URLs or unversioned downloads are present in the official installation path.

## Evidence

**Official download path:**
- URL: `https://github.com/MATPOWER/matpower/releases/download/8.1/matpower8.1.zip`
- Version pinned: Yes (version in both URL path and filename)
- Immutable: Yes (GitHub release assets are immutable once published)
- Checksum: SHA-256 `7f13b1441669a64e312d14a60e564cd91977ff1676ff77d25538e94ff313dd56` (provided via GitHub asset API and verified in `setup.sh`)

**Getting-started steps (from MATPOWER documentation):**
1. Download versioned zip from GitHub releases
2. Extract to local directory
3. Run `install_matpower` or manually `addpath(genpath('...'))`
4. Verify with `test_matpower` or `mpver`

**Artifact integrity assessment:**

| Criterion | Status |
|-----------|--------|
| Version pinned in download URL | Yes |
| Mutable URLs in install docs | No |
| Unversioned downloads | No |
| Checksum available | Yes (SHA-256 via GitHub API) |
| Reproducible install | Yes (same zip, same checksum) |

**The `setup.sh` in evaluation directory demonstrates best-practice:**
```bash
MATPOWER_VERSION="8.1"
MATPOWER_URL="https://github.com/MATPOWER/matpower/releases/download/${MATPOWER_VERSION}/matpower${MATPOWER_VERSION}.zip"
MATPOWER_SHA256="7f13b1441669a64e312d14a60e564cd91977ff1676ff77d25538e94ff313dd56"
echo "${MATPOWER_SHA256}  matpower${MATPOWER_VERSION}.zip" | sha256sum -c -
```

**No `curl | bash` patterns:** Installation does not involve piping remote scripts to a shell. The zip file is downloaded, verified, and extracted manually.

## Implications

MATPOWER's distribution model provides strong artifact integrity for getting-started workflows. Version-pinned URLs, immutable GitHub release assets, and SHA-256 checksums ensure that the same artifact is retrieved every time. This eliminates a class of supply chain attacks (dependency confusion, compromised package registries) that affect tools distributed through package managers.
