---
test_id: F-9
tool: gridcal
dimension: supply_chain
network: N/A
protocol_version: "v4"
status: qualified_pass
workaround_class: null
timestamp: 2026-03-06T05:00:00Z
---

# F-9: Dependency Surface

## Criteria

Assess the size and risk profile of the total dependency tree. Identify unusual,
unmaintained, or high-risk dependencies.

## Result: QUALIFIED PASS

The dependency surface is large (29 direct, ~83 total) with several dependencies that
are unusual for a power systems analysis engine.

### Dependency Count

| Category | Count |
|----------|-------|
| Direct runtime dependencies | 29 |
| Total installed packages | ~83 |

### Unusual or Noteworthy Dependencies

| Package | Purpose | Concern |
|---------|---------|---------|
| opencv-python | Image processing | Unexpected for power systems; large binary, wide attack surface |
| windpowerlib | Wind power modeling | Niche; adds renewable modeling deps |
| pvlib | Solar PV modeling | Niche; adds solar modeling deps |
| xlwt | Legacy Excel (.xls) writing | Unmaintained (last release 2021), Python 2 era |
| brotli | HTTP compression | Unusual for an analysis library |
| websockets | WebSocket protocol | For GUI server mode, not core analysis |
| setuptools, wheel | Build tools | Should be build-only, not runtime deps |

### Version Conflicts

- urllib3/chardet version conflict produces deprecation warnings at import time. Not
  a runtime failure but indicates imprecise version pinning.

### Risk Assessment

The core numerical stack (numpy, scipy, pandas, numba, highspy) is standard and
well-maintained. The concern is the long tail of peripheral dependencies that inflate
the attack surface and maintenance burden without contributing to core power systems
analysis.

A production deployment could benefit from a stripped-down install that excludes GUI,
renewable modeling, and legacy Excel dependencies. Currently there is no mechanism to
install a minimal subset (no extras/optional dependency groups in pyproject.toml).
