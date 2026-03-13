---
test_id: F-9
tool: pypsa
dimension: supply_chain
network: N/A
protocol_version: v9
skill_version: v1
test_hash: d3cd01ff
status: qualified_pass
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

# F-9: Getting-Started Artifact Integrity (getting_started_integrity)

## Result: QUALIFIED PASS

## Finding

PyPSA installation documentation uses unpinned `pip install pypsa` (not a `main`-branch git URL), which is sound practice. However, the official getting-started guide does not recommend pinning to a specific version, and some documentation examples link to `main`-branch notebooks on GitHub rather than tagged releases.

## Evidence

**Installation instructions (from https://pypsa.readthedocs.io/en/latest/getting-started/installation.html):**
```bash
pip install pypsa
```
This resolves to the latest PyPI release — not a git URL, not `main` branch. Acceptable for general use; production environments should pin the version.

**Version pinning in install docs:**
- No explicit version pin recommended (e.g., `pip install pypsa==1.1.2`)
- No `pip install git+https://github.com/PyPSA/PyPSA` in official docs
- PyPI resolution is safe because each PyPI release is immutable and hash-verified

**Documentation examples — mutable link check:**
- Some Jupyter notebook examples in the documentation link to `https://github.com/PyPSA/PyPSA/blob/main/examples/` (main branch)
- Main-branch notebook content can change between visits without version bumping
- The ReadTheDocs documentation itself is versioned (https://pypsa.readthedocs.io/en/v1.1.2/) — users who navigate to a versioned docs URL get stable content
- Default docs URL (https://pypsa.readthedocs.io/en/latest/) always points to the latest release tag (not `main`), which is acceptable

**Evaluation project `pyproject.toml`:**
```toml
dependencies = [
    "pypsa",        # unpinned — appropriate for evaluation; production should pin
    "pandapower",   # unpinned
    "matpowercaseframes",  # unpinned
    "highspy",      # unpinned
]
```
The evaluation project intentionally uses unpinned dependencies with `uv.lock` providing reproducibility. This is the correct pattern for lock-file-managed projects.

**Qualified pass rationale:**
The primary install path (`pip install pypsa`) is immutable-artifact-based and acceptable. The caveats are: (1) no explicit version pin recommendation in docs, and (2) some example links point to `main`-branch GitHub files. These are minor issues that do not constitute supply chain risks but represent best-practice gaps for production use.

## Implications

Getting-started integrity is B+ level. The PyPI-based install path is sound. The absence of pinned version recommendations in docs is a minor gap — sophisticated users know to pin; beginners may not. The `main`-branch notebook links in examples are a low-severity mutable-content risk (documentation drift, not security risk). No blocking supply chain integrity concerns.
