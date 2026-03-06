---
test_id: F-9
tool: pypsa
dimension: supply_chain
status: pass
timestamp: 2026-03-05
---

# F-9: Getting Started / Example Version Pinning

## Finding

PyPSA's official installation documentation demonstrates version pinning syntax for pip, conda, and uv. The pyproject.toml is referenced for the full dependency list. Examples use unpinned installs but pinning guidance is explicit.

## Evidence

**From `docs/home/installation.md` in the PyPSA repository:**

Installation commands (unpinned, for latest):

```bash
pip install pypsa
conda install -c conda-forge pypsa
uv add pypsa
```

Version pinning examples (explicitly shown):

```bash
pip install pypsa==0.35.2
conda install -c conda-forge pypsa==0.35.2
uv add pypsa==0.35.2
```

The documentation states: "any breaking changes are always announced via deprecation warnings in the code and in the release notes, including a version when they are going to be removed."

**Dependency reference:** Documentation links to the `pyproject.toml` file on GitHub for the full dependency list: "Find the full list of dependencies in the [`pyproject.toml`](https://github.com/PyPSA/PyPSA/blob/master/pyproject.toml) file."

**Evaluation project lock file:**
- `evaluations/pypsa/uv.lock` pins `pypsa==1.1.2` with SHA256 hash
- All 89 transitive dependencies are pinned with exact versions and hashes
- Fully reproducible installation via `uv sync --frozen`

**Assessment:**
- Version pinning syntax is documented
- The pyproject.toml uses lower-bound constraints (e.g., `pandas>=2.0`) rather than exact pins, which is appropriate for a library
- Lock file tooling (uv.lock) provides exact reproducibility for deployments

## Implications

The documentation adequately guides users toward version pinning. The combination of semver versioning, deprecation warnings, and lock file support via uv provides a solid reproducibility story. Pass.
