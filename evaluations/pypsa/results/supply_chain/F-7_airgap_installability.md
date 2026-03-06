---
test_id: F-7
tool: pypsa
dimension: supply_chain
status: pass
timestamp: 2026-03-05
---

# F-7: Air-Gap Installability

## Finding

PyPSA can be installed in an air-gapped environment using standard Python packaging tools (pip/uv wheel download + offline install). All dependencies are available as pre-built wheels from PyPI.

## Evidence

**Air-gap installation procedure:**

1. **Download phase (on internet-connected machine):**

   ```bash
   # Using uv (preferred)
   uv pip download pypsa --dest ./wheels/

   # Or using pip
   pip download pypsa --dest ./wheels/
   ```

2. **Transfer:** Copy the `wheels/` directory to the air-gapped machine via approved media.

3. **Install phase (on air-gapped machine):**

   ```bash
   # Using uv
   uv pip install --no-index --find-links ./wheels/ pypsa

   # Or using pip
   pip install --no-index --find-links ./wheels/ pypsa
   ```

**Feasibility assessment:**

- **PyPSA itself:** Pure Python wheel (py3-none-any) -- no compilation needed
- **linopy:** Pure Python wheel -- no compilation needed
- **highspy:** Pre-built wheels available for Linux (x86_64, aarch64), macOS (x86_64, arm64), and Windows (x86_64) -- no compilation needed
- **numpy, scipy, pandas:** Pre-built manylinux wheels available for all common platforms
- **All 89 packages:** Available as pre-built wheels on PyPI for Linux x86_64

**Lock file support:**
- `uv.lock` contains exact versions and SHA256 hashes for deterministic offline reproduction
- `uv sync --frozen` can install from a pre-populated cache directory

**Potential complications:**
- Some geo packages (pyproj, pyogrio, shapely) bundle system libraries (PROJ, GDAL, GEOS) inside their wheels; these are self-contained and do not require separate system library installation
- Total download size for all 89 packages: estimated 200-400 MB (wheels contain bundled native libraries)

**No external runtime dependencies:**
- HiGHS solver is bundled in the highspy wheel (no separate installation)
- No license server or external service required
- No runtime internet connectivity needed

## Implications

Air-gap installation is straightforward using standard Python tooling. The pre-built wheel ecosystem for scientific Python is mature. The uv.lock file provides deterministic version pinning suitable for reproducible air-gapped deployments. No unusual steps or workarounds required.
