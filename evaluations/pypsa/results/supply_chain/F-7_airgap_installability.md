---
test_id: F-7
tool: pypsa
dimension: supply_chain
network: N/A
protocol_version: v11
skill_version: v2
test_hash: 462a162d
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
loc: null
solver: null
timestamp: 2026-03-24T14:00:00Z
---

# F-7: Air-Gap Installability

## Result: PASS

## Finding

PyPSA and all 88 dependencies can be installed fully offline using standard Python packaging tools (`pip download` / `pip install --no-index`). No runtime network access is required for core power-system computation.

## Evidence

### Offline Installation Methodology

1. **Download phase** (requires network):
   ```bash
   pip download pypsa --dest ./offline_packages/
   # or: uv pip download pypsa -o ./offline_packages/
   ```

2. **Install phase** (air-gapped):
   ```bash
   pip install --no-index --find-links ./offline_packages/ pypsa
   ```

### Package Format Analysis

- **PyPSA**: Pure Python wheel (`py3-none-any.whl`). No compilation needed.
- **Platform-dependent wheels**: numpy, scipy, highspy, shapely, pyproj, pyogrio, netCDF4, Levenshtein/rapidfuzz ship pre-built manylinux wheels for Linux x86_64. All available on PyPI.
- **No source-only packages**: All 88 dependencies have pre-built wheels for common platforms.

### Runtime Network Dependencies

**None required** for core functionality:

| Feature | Network Required | Notes |
|---------|:---------------:|-------|
| `n.lpf()` (DCPF) | No | In-memory computation |
| `n.pf()` (ACPF) | No | In-memory computation |
| `n.optimize()` (OPF) | No | In-memory computation |
| File I/O (NetCDF, CSV) | No | Local filesystem only |
| GCS model storage | Yes | Optional, via google-cloud-storage |
| Remote URL loading | Yes | Optional, `pypsa.Network("https://...")` |

### Air-Gap Constraints

1. The `google-cloud-storage` transitive chain (~8 packages, ~5 MB) is downloaded but unused in air-gapped environments. Wasted space, not a functional issue.
2. Platform-specific wheels must be pre-downloaded for the target OS/architecture. manylinux wheels cover standard Linux x86_64.
3. `pip download` / `uv pip compile` handles the full transitive closure automatically.

## Implications

Fully air-gap installable with no runtime network dependencies for power-system computation. The offline installation path uses standard Python tooling with no custom steps required.
