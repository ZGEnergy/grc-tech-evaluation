---
test_id: F-2
tool: pypsa
dimension: supply_chain
slug: dependency_tree
network: N/A
protocol_version: v4
status: qualified_pass
workaround_class: null
timestamp: 2026-03-06T12:00:00Z
---

# F-2: Dependency Tree Audit

## Summary

| Metric | Value |
|--------|-------|
| Total installed packages | 87 |
| Direct PyPSA dependencies (core) | ~12 (numpy, scipy, pandas, xarray, linopy, matplotlib, geopandas, networkx, highspy, deprecation, packaging, validators) |
| Packages with compiled extensions | 7 (numpy, scipy, pandas, highspy, shapely, pyproj, pyogrio) |
| Unpinned dependencies | All deps are version-pinned via uv.lock |

## Key Packages

| Package | Version | Role |
|---------|---------|------|
| pypsa | 1.1.2 | Core modeling framework |
| linopy | 0.6.4 | Optimization backend (LP/MILP/QP) |
| highspy | 1.13.1 | HiGHS solver Python bindings |
| numpy | 2.3.5 | Numerical arrays |
| scipy | 1.16.3 | Sparse matrices, linear algebra |
| pandas | 2.3.3 | DataFrames for component data |
| xarray | 2026.2.0 | N-D array operations |
| networkx | 3.6.1 | Graph algorithms |
| geopandas | 1.1.2 | Geospatial data (plotting) |
| matplotlib | 3.10.8 | Visualization |

## Dependency Categories

**Essential runtime** (cannot function without):
numpy, scipy, pandas, xarray, linopy, highspy, networkx, deprecation, packaging

**Visualization/optional** (could be removed for headless use):
matplotlib, geopandas, shapely, pyproj, pyogrio, pydeck, plotly, seaborn, pillow

**Test/evaluation extras** (not core PyPSA deps):
pandapower, matpowercaseframes, pandera, pytest, polars

**Infrastructure** (transitive, pulled in by above):
google-cloud-storage, requests, cryptography, protobuf, dask, etc.

## Full Package List

```
annotated-types==0.7.0, bottleneck==1.6.0, certifi==2026.2.25, cffi==2.0.0,
cftime==1.6.5, charset-normalizer==3.4.4, click==8.3.1, cloudpickle==3.1.2,
contourpy==1.3.3, cryptography==46.0.5, cycler==0.12.1, dask==2026.1.2,
deepdiff==8.6.1, deprecation==2.1.0, fonttools==4.61.1, fsspec==2026.2.0,
geojson==3.2.0, geopandas==1.1.2, google-api-core==2.30.0, google-auth==2.48.0,
google-cloud-core==2.5.0, google-cloud-storage==3.9.0, google-crc32c==1.8.0,
google-resumable-media==2.8.0, googleapis-common-protos==1.72.0, highspy==1.13.1,
idna==3.11, iniconfig==2.3.0, jinja2==3.1.6, kiwisolver==1.4.9,
levenshtein==0.27.3, linopy==0.6.4, locket==1.0.0, markupsafe==3.0.3,
matplotlib==3.10.8, matpowercaseframes==2.0.1, mypy-extensions==1.1.0,
narwhals==2.17.0, netcdf4==1.7.3, networkx==3.6.1, numexpr==2.14.1,
numpy==2.3.5, orderly-set==5.5.0, packaging==25.0, pandapower==3.4.0,
pandas==2.3.3, pandera==0.26.1, partd==1.4.2, pillow==12.1.1, plotly==6.6.0,
pluggy==1.6.0, polars==1.38.1, polars-runtime-32==1.38.1, proto-plus==1.27.1,
protobuf==6.33.5, pyasn1==0.6.2, pyasn1-modules==0.4.2, pycparser==3.0,
pydantic==2.12.5, pydantic-core==2.41.5, pydeck==0.9.1, pygments==2.19.2,
pyogrio==0.12.1, pyparsing==3.3.2, pyproj==3.7.2, pypsa==1.1.2, pytest==9.0.2,
python-dateutil==2.9.0.post0, pytz==2026.1.post1, pyyaml==6.0.3,
rapidfuzz==3.14.3, requests==2.32.5, rsa==4.9.1, scipy==1.16.3,
seaborn==0.13.2, shapely==2.1.2, six==1.17.0, toolz==1.1.0, tqdm==4.67.3,
typeguard==4.5.1, typing-extensions==4.15.0, typing-inspect==0.9.0,
typing-inspection==0.4.2, tzdata==2025.3, urllib3==2.6.3, validators==0.35.0,
xarray==2026.2.0
```

## Assessment

**QUALIFIED PASS** -- 87 total packages is a moderate dependency footprint. The core runtime path (pypsa -> linopy -> highspy) is lean. However, the visualization stack (geopandas, shapely, pyproj, pyogrio) pulls in geospatial C libraries that add supply chain surface area. These are optional for headless production use but installed by default. All dependencies are version-locked via uv.lock, eliminating unpinned dependency risk.
