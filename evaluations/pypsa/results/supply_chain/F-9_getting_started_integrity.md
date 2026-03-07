---
test_id: F-9
tool: pypsa
dimension: supply_chain
slug: getting_started_integrity
network: N/A
protocol_version: v4
status: qualified_pass
workaround_class: null
timestamp: 2026-03-06T18:00:00Z
---

# F-9: Getting-Started Artifact Integrity

## Summary

| Metric | Value |
|--------|-------|
| PyPI package version-pinned | Yes (standard semver) |
| Example network downloads version-tagged | Yes (since v0.35.0) |
| Documentation versioned | Yes (ReadTheDocs-style, per-release) |
| Tutorials in-repo (not external mutable URLs) | Yes (Jupyter notebooks in `docs/examples/`) |
| Mutable URLs in getting-started path | 1 (version check hits GitHub API) |

## Version Pinning Analysis

### Installation

Standard installation via pip/uv installs a specific version:

```bash
pip install pypsa           # installs latest release (1.1.2)
pip install pypsa==1.1.2    # explicit pin
```

The `pyproject.toml` uses standard version specifiers for dependencies. The `uv.lock` file provides full reproducibility with exact version pins for all transitive dependencies.

### Example Network Downloads

The `pypsa.examples` module (e.g., `pypsa.examples.ac_dc_meshed()`) downloads network files from GitHub. The URL construction in `pypsa/examples.py` is version-aware:

```python
def _repo_url(master=False, url="https://github.com/PyPSA/PyPSA/raw/"):
    if master or parse_version(__version_base__) < parse_version("0.35.0"):
        return f"{url}master/"
    return f"{url}v{__version_base__}/"
```

For PyPSA >= 0.35.0 (including current 1.1.2), example files are fetched from the version-tagged URL (e.g., `v1.1.2/`), not from `master`. This prevents version drift between the installed package and the example data.

### Documentation

PyPSA documentation is hosted at `docs.pypsa.org` with per-version URLs (e.g., `docs.pypsa.org/v1.0.0/`). The `stable` URL resolves to the latest release. Historical versions remain accessible.

### Tutorials

30+ Jupyter notebook tutorials are stored in-repo under `docs/examples/`:

- `example-1.ipynb`, `example-2.ipynb`, `example-3.ipynb` (basic usage)
- `capacity-expansion-planning-single-node.ipynb`
- `ac-dc-lopf.ipynb`
- `committable-extendable.ipynb`
- `chained-hydro-reservoirs.ipynb`
- And ~25 more covering specific features

These notebooks are part of the repository and are tagged with each release. They do not reference external mutable URLs for data.

## Flagged Items

### Version Check Network Call

On import, PyPSA may query `https://api.github.com/repos/PyPSA/PyPSA/releases/latest` to check for newer versions. This is:

- Gated by `pypsa.options.set_option("general.allow_network_requests", False)`
- Non-blocking (failure is silently caught)
- Not required for any functionality

However, it represents a mutable external dependency in the default getting-started path.

### PyPSA.org Website

The official website (`pypsa.org`) provides a quick-start code snippet without version pinning:

```python
import pypsa
n = pypsa.Network()
```

This is standard for library websites and not a versioning concern, as the import uses whatever version is locally installed.

## Assessment

**QUALIFIED PASS** -- PyPSA demonstrates good version hygiene. Installation is version-pinned via standard Python packaging. Example network downloads use version-tagged GitHub URLs (not `master`) since v0.35.0. Documentation is versioned per release. Tutorials are in-repo Jupyter notebooks shipped with the tagged source. The only concern is the optional GitHub API version-check call on import, which hits a mutable endpoint but is gated by configuration and non-functional.
