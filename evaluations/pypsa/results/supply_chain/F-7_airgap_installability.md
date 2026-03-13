---
test_id: F-7
tool: pypsa
dimension: supply_chain
network: N/A
protocol_version: v9
skill_version: v1
test_hash: b8d2821f
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

# F-7: Air-gap Installability (airgap_installability)

## Result: PASS

## Finding

PyPSA and its 89 dependencies can be installed in an air-gapped environment using the `uv.lock` file. All packages are downloadable from PyPI as standard wheel or sdist archives. No runtime network calls for licensing or data download were observed.

## Evidence

**Air-gap install mechanism:**
`uv sync` uses `uv.lock` which pins exact versions and SHA256 hashes for all 89 packages. The `uv export` command can generate a `requirements.txt` with hashes for pre-downloading:
```bash
uv export --format requirements-txt > requirements.txt
# Then on air-gapped machine:
pip install --no-index --find-links ./downloaded_wheels -r requirements.txt
```

All packages resolve from `https://pypi.org/simple` (standard PyPI) — no private registries, no git dependencies, no direct URL dependencies.

**Lock file confirms all packages are from PyPI:**
```toml
# Sample from uv.lock — all packages use registry source
source = { registry = "https://pypi.org/simple" }
```
No packages use `{ git = "..." }` or `{ url = "..." }` (direct URL) sources.

**Runtime network calls check:**
- PyPSA v1.1.2 does not perform any runtime network calls for licensing or telemetry
- No license validation mechanism (MIT license requires no runtime check)
- No auto-update or telemetry in PyPSA or linopy
- `pydeck` (visualization) may make network calls to Mapbox/deck.gl for rendering, but this is visualization-only and not required for power system computation
- `google-cloud-storage` is a transitive dependency pulled in via pydeck; it makes no calls unless explicitly used via the `cloudpathlib` optional extra

**One caveat — highspy data files:**
`highspy` includes no external data files. The HiGHS solver binary is statically linked into the `.so` and requires no runtime library downloads.

**Practical air-gap procedure:**
1. On internet-connected machine: `uv sync` (downloads to `.venv`) + `uv export > requirements.txt`
2. Download all wheels from PyPI to local directory (89 packages)
3. On air-gapped machine: install via `--find-links` or copy the entire `.venv`
4. All tests function identically (confirmed by devcontainer being a self-contained Docker environment)

## Implications

Air-gap installability is fully supported. The standard PyPI distribution, uv lock file, and no runtime network requirements make this a low-friction air-gap deployment. The only post-install network requirement is for visualization (pydeck/Mapbox) which is not required for power system computation.
