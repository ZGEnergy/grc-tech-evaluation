---
test_id: F-6
tool: pypsa
dimension: supply_chain
network: N/A
protocol_version: v9
skill_version: v1
test_hash: 65965672
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
timestamp: 2026-03-11T00:00:00Z
---

# F-6: Distribution Integrity (distribution_integrity)

## Result: PASS

## Finding

PyPSA is distributed via PyPI with versioned releases, both source distributions and wheels. The `uv.lock` file provides SHA256 hashes for all packages, ensuring integrity. No mutable download links are present in documentation.

## Evidence

**PyPI distribution:** https://pypi.org/project/pypsa/

- Package: `pypsa`
- Current version: 1.1.2 (latest as of 2026-02-23)
- Distribution formats available:
  - Source distribution (sdist): `pypsa-1.1.2.tar.gz`
  - Pure Python wheel: `pypsa-1.1.2-py3-none-any.whl` (no compiled extensions — pure Python)

**Versioned releases:** Yes — standard semver versioning. Each release is tagged and published to PyPI independently. Version history shows consistent release cadence.

**Lock file integrity (from `uv.lock` sample):**
```toml
[[package]]
name = "pypsa"
version = "1.1.2"
source = { registry = "https://pypi.org/simple" }
sdist = { url = "https://files.pythonhosted.org/packages/.../pypsa-1.1.2.tar.gz",
          hash = "sha256:<hash>", ... }
wheels = [
    { url = "https://files.pythonhosted.org/packages/.../pypsa-1.1.2-py3-none-any.whl",
      hash = "sha256:<hash>", ... }
]
```
All packages in `uv.lock` include `hash = "sha256:<hash>"` — content-addressable, tamper-evident.

**Mutable URLs check:** Documentation at https://pypsa.readthedocs.io/ links to versioned PyPI packages, not to `main`/`master` branch tarballs. Installation instructions use `pip install pypsa` (PyPI-resolved, not git URL). No `git+https://github.com/...` links in official install docs.

**GitHub releases:** https://github.com/PyPSA/PyPSA/releases — each release has a tagged commit, release notes, and links to the corresponding PyPI upload.

## Implications

Distribution integrity is excellent. SHA256-hashed lock file, versioned PyPI releases, pure-Python wheel (no platform-specific binaries for PyPSA itself), and no mutable download links. The supply chain is reproducible and auditable. No concerns.
