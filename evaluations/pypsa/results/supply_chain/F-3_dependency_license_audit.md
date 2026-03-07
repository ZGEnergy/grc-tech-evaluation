---
test_id: F-3
tool: pypsa
dimension: supply_chain
slug: dependency_license_audit
network: N/A
protocol_version: v4
status: qualified_pass
workaround_class: null
timestamp: 2026-03-06T18:00:00Z
---

# F-3: Dependency License Audit

## Summary

| Metric | Value |
|--------|-------|
| Total packages audited | 90 |
| Permissive licenses (MIT, BSD, Apache, PSF) | 87 |
| Copyleft licenses (GPL) | 1 |
| Unknown/unclassified licenses | 1 |
| Proprietary licenses | 0 |

## Flagged Packages

### GPL-licensed: Levenshtein 0.27.3

- **License:** GPL-2.0-or-later
- **Dependency path:** PyPSA (direct) -> Levenshtein
- **Usage:** Imported at runtime in `pypsa/network/transform.py` (`from Levenshtein import distance`) for fuzzy-matching attribute names to provide helpful error messages.
- **Risk:** GPL-2.0-or-later is a strong copyleft license. If PyPSA is distributed as part of a proprietary application, the GPL requires that the entire combined work be licensed under GPL. However, Levenshtein is used only for developer-facing error messages (checking if a misspelled attribute is close to a valid one), not for any power system computation. The companion package RapidFuzz (MIT licensed) could serve as a drop-in replacement.
- **Mitigation:** For internal use (not redistribution), GPL poses no practical constraint. If redistribution is required, replace `Levenshtein` with `RapidFuzz` (already installed, MIT licensed) or remove the fuzzy-match feature.

### Unknown License: google-crc32c 1.8.0

- **License field:** UNKNOWN (metadata not populated)
- **Actual license:** Apache-2.0 (confirmed via PyPI and source repository)
- **Dependency path:** google-cloud-storage -> google-resumable-media -> google-crc32c
- **Risk:** None. This is a Google-maintained package under Apache-2.0; the UNKNOWN field is a packaging metadata omission.
- **Note:** google-crc32c and the entire google-cloud-storage chain are transitive dependencies pulled in by the evaluation environment, not by PyPSA core.

## Full License Inventory

| License Category | Count | Packages |
|-----------------|-------|----------|
| MIT | 38 | pypsa, linopy, highspy, cffi, cftime, charset-normalizer, deepdiff, fonttools, iniconfig, markupsafe, matpowercaseframes, mypy_extensions, narwhals, netCDF4, numexpr, orderly-set, pandera, pillow, plotly, pluggy, polars, polars-runtime-32, pydantic, pydantic_core, pyogrio, pyparsing, pyproj, pytest, pytz, pyyaml, six, tqdm, typeguard, typing-inspect, typing-inspection, urllib3, validators, RapidFuzz |
| BSD (all variants) | 28 | numpy, scipy, pandas, networkx, geopandas, shapely, seaborn, bottleneck, click, cloudpickle, contourpy, cycler, dask, fsspec, geojson, idna, kiwisolver, locket, packaging, pandapower, partd, protobuf, pyasn1, pyasn1_modules, pycparser, toolz, cryptography (dual), pydeck (Apache) |
| Apache-2.0 | 13 | deprecation, google-api-core, google-auth, google-cloud-core, google-cloud-storage, google-resumable-media, googleapis-common-protos, proto-plus, pydeck, requests, rsa, tzdata, xarray |
| PSF | 3 | matplotlib, typing_extensions, certifi (MPL 2.0) |
| MPL-2.0 | 1 | certifi |
| GPL-2.0-or-later | 1 | Levenshtein |
| UNKNOWN | 1 | google-crc32c (actually Apache-2.0) |
| Dual (Apache OR BSD) | 2 | cryptography, packaging |

## Assessment

**QUALIFIED PASS** -- 87 of 90 packages carry permissive licenses (MIT, BSD, Apache, PSF). One package (Levenshtein) carries a GPL-2.0-or-later license, which is a copyleft concern for redistribution scenarios. However:

1. Levenshtein is used only for developer UX (fuzzy attribute name matching), not computational functionality.
2. For internal use without redistribution, GPL poses no legal constraint.
3. RapidFuzz (MIT) is already installed and could replace Levenshtein with minimal code changes.
4. The one UNKNOWN license (google-crc32c) is confirmed Apache-2.0 via source inspection.

No proprietary or restrictive commercial licenses were found in the dependency tree.
