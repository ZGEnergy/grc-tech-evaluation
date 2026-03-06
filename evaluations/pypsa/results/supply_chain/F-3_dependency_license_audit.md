---
test_id: F-3
tool: pypsa
dimension: supply_chain
status: qualified_pass
timestamp: 2026-03-05
---

# F-3: Dependency License Audit

## Finding

All runtime dependencies use permissive licenses (MIT, BSD, Apache-2.0) except one: **Levenshtein (GPL-2.0-or-later)**, which is a direct PyPSA dependency. The GPL dependency creates a copyleft concern but does not block deployment.

## Evidence

License audit performed via `importlib.metadata` inside the devcontainer. Results organized by license family:

### MIT / MIT-compatible
annotated-types, bottleneck (BSD), cffi, cftime, charset-normalizer, click (BSD-3), cloudpickle (BSD-3), contourpy (BSD-3), deepdiff, deprecation (Apache-2.0), fonttools, fsspec (BSD-3), geojson (BSD), geopandas (BSD-3), highspy, idna (BSD-3), jinja2 (BSD), kiwisolver (BSD), linopy, locket (BSD-2), markupsafe (BSD-3), matpowercaseframes, narwhals, netcdf4, networkx (BSD-3), numexpr, numpy (BSD-3), orderly-set, packaging (Apache), pandapower (BSD), pandas (BSD-3), pandera, plotly, pydantic, pydantic-core, pydeck (Apache-2.0), pygments (BSD-2), pyogrio, pyparsing, pyproj, pypsa, pytz, pyyaml, rapidfuzz, scipy (BSD-3), seaborn (BSD), shapely (BSD-3), six, toolz (BSD-3), typeguard, typing-extensions (PSF-2.0), typing-inspect, typing-inspection, validators, xarray (Apache-2.0)

### Apache-2.0
certifi (MPL-2.0), cryptography (Apache-2.0 OR BSD-3), google-api-core, google-auth, google-cloud-core, google-cloud-storage, google-crc32c, google-resumable-media, googleapis-common-protos, proto-plus, protobuf (BSD-3), pyasn1 (BSD-2), pyasn1-modules (BSD), requests, rsa, tzdata, urllib3

### MPL-2.0
certifi (MPL-2.0), tqdm (MPL-2.0 AND MIT)

### GPL-2.0-or-later (COPYLEFT)
**levenshtein (0.27.3)** -- GPL-2.0-or-later, confirmed via LICENSE file at <https://github.com/rapidfuzz/Levenshtein>

### Analysis of Levenshtein GPL concern

- **Levenshtein is a direct PyPSA dependency** (listed in pypsa's pyproject.toml dependencies)
- Used for fuzzy string matching (likely in component name matching / error messages)
- The GPL-2.0-or-later license requires that derivative works also be GPL-licensed
- **Mitigation:** PyPSA is MIT-licensed; using a GPL library as a dependency does not relicense PyPSA itself, but any distributed binary that links Levenshtein would need to comply with GPL terms
- **Practical impact for this evaluation:** Low. The Levenshtein library is used for user convenience (fuzzy matching of component names), not for core power system calculations. It could likely be replaced with `rapidfuzz` (MIT) or removed without affecting computational functionality.

### Dual-licensed / Unusual
- python-dateutil: "Dual License" (Apache-2.0 and BSD-3)
- polars: MIT (confirmed via GitHub)
- cycler: BSD-style (matplotlib project)

## Implications

The dependency license landscape is overwhelmingly permissive (MIT/BSD/Apache). The sole GPL dependency (Levenshtein) is a direct PyPSA dep but is used for non-critical string matching functionality. For government deployment in an air-gapped environment where distribution is involved, the GPL dependency should be noted in procurement documentation. However, since PyPSA is used as a library (not distributed as a combined work), the practical risk is low. Qualified pass -- the GPL dep is documented and manageable but should be flagged.
