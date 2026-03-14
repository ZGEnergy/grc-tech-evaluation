---
test_id: F-7
tool: pypsa
dimension: supply_chain
network: N/A
status: pass
workaround_class: null
timestamp: 2026-03-13T12:00:00Z
protocol_version: v10
skill_version: v1
test_hash: 462a162d
---

# F-7: Air-Gap Installability

## Findings

### Offline Installation Feasibility

**Yes, fully feasible.** PyPSA and all dependencies can be installed
offline using standard Python packaging tools.

### Methodology

1. **Download phase** (requires network):
   ```bash
   pip download pypsa --dest ./offline_packages/
   ```
   This downloads PyPSA and all transitive dependencies as wheel files.

2. **Install phase** (air-gapped):
   ```bash
   pip install --no-index --find-links ./offline_packages/ pypsa
   ```

### Package Format Analysis

- **PyPSA itself**: Pure Python wheel (`py3-none-any.whl`). No
  platform-specific compilation needed.
- **Platform-dependent wheels**: numpy, scipy, highspy, shapely, pyproj,
  pyogrio, netCDF4, and Levenshtein/rapidfuzz ship pre-built wheels for
  Linux (manylinux), macOS, and Windows. These wheels must be downloaded
  for the target platform.
- **No source-only packages**: All dependencies have pre-built wheels
  available on PyPI for common platforms.

### Runtime Network Dependencies

**No runtime network access required** for core functionality:
- Power flow (`n.lpf()`, `n.pf()`) operates entirely in-memory
- Optimization (`n.optimize()`) operates entirely in-memory
- File I/O (NetCDF, CSV, HDF5) uses local filesystem only

Optional features that require network access:
- `google-cloud-storage` integration (for loading/saving models to GCS)
- Remote URL loading via `pypsa.Network("https://...")`
- The `certifi` CA bundle is pulled as a dependency but is not used in
  core computation

### Air-Gap Constraints

1. The `google-cloud-storage` dependency chain (~8 packages) will be
   downloaded but serves no purpose in an air-gapped environment. This
   is wasted space (~5 MB) but not a functional issue.
2. Platform-specific wheels must be pre-downloaded for the exact OS/arch
   combination. For Linux x86_64 (the evaluation platform), manylinux
   wheels are available for all packages.
3. `pip download` or `uv pip compile` handles the full transitive closure
   automatically.

## Recorded Metrics

- offline_installable: yes (via pip download + pip install --no-index)
- runtime_network_deps: none for core functionality; optional GCS and
  remote URL features require network
