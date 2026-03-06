---
test_id: F-6
tool: pypsa
dimension: supply_chain
status: pass
timestamp: 2026-03-05
---

# F-6: Distribution Integrity

## Finding

PyPSA is distributed via PyPI and conda-forge with automated release pipelines, sdist + wheel artifacts, and version-pinned lock file support via uv.

## Evidence

**Distribution channels:**

1. **PyPI** (primary):
   - Package: <https://pypi.org/project/pypsa/>
   - Current version: 1.1.2
   - Artifacts: sdist (.tar.gz) + universal wheel (py3-none-any.whl)
   - Upload timestamps recorded in lock file metadata
   - SHA256 hashes in uv.lock for every artifact

2. **conda-forge**:
   - Package: `conda install -c conda-forge pypsa`
   - Available per installation docs

3. **GitHub Releases**:
   - Automated via `.github/workflows/release.yml`
   - Tagged releases match PyPI versions

**Integrity mechanisms:**
- `uv.lock` contains SHA256 hashes for every wheel and sdist:

  ```
  sdist = { url = "...", hash = "sha256:5d8ac5e1...", size = 12985258 }
  wheels = [{ url = "...", hash = "sha256:5b48e6cf...", size = 347349 }]
  ```

- `uv sync` verifies hashes on install
- PyPSA is a pure Python package (py3-none-any wheel) -- no platform-specific build concerns for the core package
- Upload timestamps are recorded for provenance tracking

**Release automation:**
- GitHub Actions release workflow builds and publishes to PyPI
- `setuptools_scm` generates version numbers from git tags
- `hynek/build-and-inspect-python-package` action validates package metadata

**Version history integrity:**
- Continuous version numbering from v0.1 through v1.1.2
- No yanked versions observed
- Release notes maintained in `docs/release-notes.md`

## Implications

Distribution integrity is strong. The combination of PyPI distribution with hash verification in uv.lock, automated release pipelines, and reproducible builds (pure Python wheel) provides high confidence in artifact authenticity. No custom or unusual distribution mechanisms.
