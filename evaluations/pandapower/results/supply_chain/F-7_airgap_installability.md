---
test_id: F-7
tool: pandapower
dimension: supply_chain
network: N/A
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: null
peak_memory_mb: null
loc: null
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# F-7: Airgap Installability

## Result: PASS

## Finding

pandapower and all its dependencies can be installed fully offline. The package is pure
Python (no build-time compilation required for the core), and all dependencies are available
as pre-built wheels on PyPI. No runtime network access is required for power flow
computation.

## Evidence

### Offline installation procedure

1. **Download phase (on internet-connected machine):**
   ```bash
   pip download pandapower[performance] -d ./wheels/
   ```
   This collects all wheels (and sdists where wheels are unavailable) into a local directory.

2. **Install phase (on airgapped machine):**
   ```bash
   pip install --no-index --find-links=./wheels/ pandapower[performance]
   ```

### Wheel availability

- pandapower itself: `py3-none-any` wheel (platform-independent).
- numpy, scipy, pandas: manylinux wheels for all supported platforms on PyPI.
- LightSim2Grid: manylinux wheels on PyPI.
- numba, llvmlite: manylinux wheels on PyPI.
- ortools: manylinux wheels on PyPI.
- All other deps: pure Python or provide manylinux wheels.

### Runtime network dependencies

- **None.** pandapower does not contact any external service at runtime.
- Network test data (e.g., `pp.networks.case9()`) is generated in-memory from hardcoded
  data, not downloaded.
- The `pandapower.converter` module reads local files only.

### Caveats

- The optional `PowerModels.jl` bridge (via `juliacall`) would require Julia and its package
  registry, which is harder to airgap. However, this is an optional extra (`[pandamodels]`),
  not part of the core or performance install.
- Simbench data downloads are a separate package (`simbench`), not a pandapower dependency.

## Implications

pandapower is fully airgap-installable for the core + performance configuration. The wheel
ecosystem for all dependencies is mature. No runtime phone-home behavior. This is the
ideal outcome for deployment in isolated or high-security environments.
