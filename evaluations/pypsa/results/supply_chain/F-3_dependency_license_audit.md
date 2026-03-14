---
test_id: F-3
tool: pypsa
dimension: supply_chain
network: N/A
status: qualified_pass
workaround_class: null
timestamp: 2026-03-13T12:00:00Z
protocol_version: v10
skill_version: v1
test_hash: 15e985d9
---

# F-3: Dependency License Audit

## Findings

### License Inventory

All runtime dependencies were audited via `importlib.metadata`. Licenses
grouped by type:

#### Permissive (MIT, BSD, Apache 2.0, PSF) — No Concerns

| Package | License | Type |
|---------|---------|------|
| pypsa | MIT | Core |
| numpy | BSD 3-Clause | Computation |
| scipy | BSD 3-Clause | Computation |
| pandas | BSD 3-Clause | Data |
| xarray | Apache 2.0 | Data |
| linopy | MIT | Optimization |
| highspy | MIT | Solver |
| matplotlib | PSF | Visualization |
| plotly | MIT | Visualization |
| seaborn | BSD 3-Clause | Visualization |
| networkx | BSD 3-Clause | Graph |
| geopandas | BSD 3-Clause | Geospatial |
| shapely | BSD 3-Clause | Geospatial |
| deprecation | Apache 2.0 | Utility |
| validators | MIT | Utility |
| rapidfuzz | MIT | Utility (transitive) |
| pydantic | MIT | Validation |
| pandera | MIT | Validation |
| requests | Apache 2.0 | HTTP |
| google-cloud-storage | Apache 2.0 | Cloud |
| google-api-core | Apache 2.0 | Cloud |
| google-auth | Apache 2.0 | Cloud |
| jinja2 | BSD 3-Clause | Template |
| pillow | HPND | Image |
| polars | MIT | Data |
| dask | BSD 3-Clause | Parallel |

#### Weak Copyleft (MPL-2.0) — Low Concern

| Package | License | Notes |
|---------|---------|-------|
| certifi | MPL-2.0 | CA certificate bundle. File-level copyleft only — does not propagate to calling code. Standard in Python ecosystem. |
| tqdm | MPL-2.0 AND MIT | Dual-licensed. MIT option available. |

#### Strong Copyleft (GPL) — FLAGGED

| Package | License | Notes |
|---------|---------|-------|
| **Levenshtein** | **GPL-2.0-or-later** | Direct dependency of PyPSA. Used for fuzzy string matching in component name validation. |

### Levenshtein GPL-2.0 Analysis

**License-Expression** (from package metadata): `GPL-2.0-or-later`

**Usage in PyPSA**: The `levenshtein` package is imported in PyPSA's
component validation code to suggest corrections when users mistype
component attribute names. It is a convenience feature, not a
computational dependency.

**Risk assessment**:
- The GPL-2.0-or-later license requires that derivative works be
  distributed under GPL-compatible terms
- Whether importing a GPL library makes the importing code a "derivative
  work" is a legal gray area, but the conservative interpretation (FSF
  position) is that it does
- PyPSA itself is MIT-licensed, which is GPL-compatible for distribution
  purposes (MIT code can be incorporated into GPL projects, but the reverse
  requires the combined work to be GPL)
- For ZGE's use case (internal use, not redistribution), GPL does not
  impose additional obligations
- For redistribution scenarios, legal counsel should evaluate

**Mitigation**: The `levenshtein` package could be replaced with the
MIT-licensed `rapidfuzz` (which is already a transitive dependency of
`levenshtein`) or the functionality could be made optional.

### Packages with Unclear License Metadata

Several packages lack explicit license fields in their metadata but have
OSI-approved classifiers or well-known licenses:

| Package | Metadata | Actual License |
|---------|----------|----------------|
| cffi | No field | MIT (PyPI) |
| click | No field | BSD 3-Clause (PyPI) |
| cryptography | No field | Apache 2.0 / BSD (dual) |
| dask | No field | BSD 3-Clause (PyPI) |
| idna | No field | BSD 3-Clause (PyPI) |
| netCDF4 | No field | MIT (PyPI) |
| pyomo | No field | BSD 3-Clause (PyPI) |
| pydantic | No field | MIT (PyPI) |

All verified as permissive upon manual PyPI check.

## Qualification Reason

Qualified pass due to the GPL-2.0-or-later `levenshtein` dependency.
This is a direct dependency declared in PyPSA's `pyproject.toml`. While
it does not affect internal-use-only deployments, it creates a copyleft
concern for redistribution scenarios.

## Recorded Metrics

- flagged_licenses: 1 (Levenshtein: GPL-2.0-or-later)
