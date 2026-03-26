---
test_id: F-3
tool: pypsa
dimension: supply_chain
network: N/A
protocol_version: v11
skill_version: v2
test_hash: ac2a9361
status: qualified_pass
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
loc: null
solver: null
timestamp: 2026-03-24T14:00:00Z
---

# F-3: Dependency License Audit

## Result: QUALIFIED PASS

## Finding

One direct dependency (`Levenshtein`) carries a GPL-2.0-or-later license (strong copyleft). Two transitive dependencies (`certifi`, `tqdm`) carry MPL-2.0 (weak copyleft). All remaining 85 packages are permissively licensed (MIT, BSD, Apache 2.0, PSF, HPND). A `license-flags` observation has been emitted.

## Evidence

Full license audit of all 88 installed packages performed via `importlib.metadata` on 2026-03-24. Every direct and transitive runtime dependency was checked.

### Permissive Licenses (No Concerns) — 85 packages

| Package | Version | License |
|---------|---------|---------|
| pypsa | 1.1.2 | MIT |
| numpy | 2.3.5 | BSD 3-Clause |
| scipy | 1.16.3 | BSD 3-Clause |
| pandas | 2.3.3 | BSD 3-Clause |
| xarray | 2026.2.0 | Apache 2.0 |
| linopy | 0.6.4 | MIT |
| highspy | 1.13.1 | MIT |
| matplotlib | 3.10.8 | PSF/matplotlib |
| plotly | 6.6.0 | MIT |
| seaborn | 0.13.2 | BSD 3-Clause |
| networkx | 3.6.1 | BSD 3-Clause |
| geopandas | 1.1.2 | BSD 3-Clause |
| shapely | 2.1.2 | BSD 3-Clause |
| deprecation | 2.1.0 | Apache 2.0 |
| validators | 0.35.0 | MIT |
| RapidFuzz | 3.14.3 | MIT |
| pydantic | 2.12.5 | MIT |
| pandera | 0.26.1 | MIT |
| requests | 2.32.5 | Apache 2.0 |
| google-cloud-storage | 3.9.0 | Apache 2.0 |
| google-api-core | 2.30.0 | Apache 2.0 |
| google-auth | 2.48.0 | Apache 2.0 |
| google-cloud-core | 2.5.0 | Apache 2.0 |
| google-crc32c | 1.8.0 | Apache 2.0 (PyPI verified; metadata field empty) |
| google-resumable-media | 2.8.0 | Apache 2.0 |
| googleapis-common-protos | 1.72.0 | Apache 2.0 |
| dask | 2026.1.2 | BSD 3-Clause |
| polars | 1.38.1 | MIT |
| pillow | 12.1.1 | MIT-CMU (HPND) |
| Jinja2 | 3.1.6 | BSD |
| netCDF4 | 1.7.3 | MIT |
| pydeck | 0.9.1 | Apache 2.0 |
| cryptography | 46.0.5 | Apache 2.0 / BSD 3-Clause (dual) |
| cffi | 2.0.0 | MIT |
| click | 8.3.1 | BSD 3-Clause |
| idna | 3.11 | BSD 3-Clause |
| pyomo | 6.10.0 | BSD 3-Clause |
| packaging | 25.0 | Apache 2.0 |
| typing_extensions | 4.15.0 | PSF-2.0 |
| (remaining ~47 packages) | various | MIT/BSD/Apache 2.0 |

### Weak Copyleft (MPL-2.0) — Low Concern

| Package | Version | License | Notes |
|---------|---------|---------|-------|
| certifi | 2026.2.25 | MPL-2.0 | CA certificate bundle. File-level copyleft only; does not propagate to calling code. Standard in virtually all Python HTTP stacks. |
| tqdm | 4.67.3 | MPL-2.0 AND MIT | Dual-licensed. MIT option available, so MPL does not apply. |

### Strong Copyleft (GPL) — FLAGGED

| Package | Version | License | Notes |
|---------|---------|---------|-------|
| **Levenshtein** | **0.27.3** | **GPL-2.0-or-later** | Direct dependency of PyPSA. Used for fuzzy string matching in component name validation (UX feature, not computational). |

### Packages with Unclear Metadata (Verified Manually)

| Package | Metadata Status | Verified License |
|---------|----------------|-----------------|
| google-crc32c | No License field or classifiers | Apache 2.0 (verified on PyPI) |
| cycler | License text only (no SPDX) | BSD 3-Clause (classifier: OSI Approved :: BSD License) |
| kiwisolver | License text only (no SPDX) | BSD 3-Clause (classifier: OSI Approved :: BSD License) |

### Levenshtein GPL-2.0 Analysis

- **License-Expression**: `GPL-2.0-or-later` (confirmed from package metadata)
- **Usage in PyPSA**: Imported in component validation code for fuzzy matching of mistyped attribute names. Convenience/UX feature, not computational.
- **Conservative interpretation** (FSF position): importing a GPL library makes the combined work a derivative, requiring GPL-compatible distribution terms.
- **Internal use**: GPL imposes no additional obligations for internal-only use (no redistribution).
- **Mitigation**: Replaceable with `rapidfuzz` (MIT, already a transitive dependency of Levenshtein) or could be made optional.

## Workarounds

- **What:** The GPL-2.0 `levenshtein` dependency can be replaced with `rapidfuzz` (MIT) for fuzzy matching, or the import can be made optional.
- **Why:** GPL-2.0-or-later creates copyleft propagation risk in redistribution scenarios.
- **Durability:** stable — rapidfuzz is already installed as a transitive dependency; switching requires a one-line code change in PyPSA.
- **Grade impact:** Qualified pass rather than full pass due to the copyleft finding. Does not affect internal-use deployments.

## Implications

The single GPL dependency is a known issue in the PyPSA community. For ZGE's internal-use scenario, this carries no legal obligation. For redistribution scenarios, legal counsel should evaluate. The `license-flags` observation documents this finding for downstream consumption.
