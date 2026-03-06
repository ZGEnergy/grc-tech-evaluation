---
test_id: F-2
tool: pypsa
dimension: supply_chain
status: pass
timestamp: 2026-03-05
---

# F-2: Full Dependency Enumeration

## Finding

PyPSA's resolved dependency tree contains 89 packages (including the evaluation project itself). The dependency graph is well-structured with clear layers.

## Evidence

Lock file: `evaluations/pypsa/uv.lock` (89 packages resolved)

**PyPSA direct dependencies (from lock file):**
1. deprecation
2. geopandas
3. highspy
4. levenshtein
5. linopy
6. matplotlib
7. netcdf4
8. networkx
9. numpy
10. pandas
11. plotly
12. pydeck
13. scipy
14. seaborn
15. shapely
16. validators
17. xarray

**Evaluation project additional direct deps:**
- pandapower (adds deepdiff, geojson, pandera, tqdm, polars, etc.)
- matpowercaseframes
- highspy (also a PyPSA dep)

**Full resolved package list (89 packages):**

| Package | Version | Category |
|---------|---------|----------|
| annotated-types | 0.7.0 | validation |
| bottleneck | 1.6.0 | numpy acceleration |
| certifi | 2026.2.25 | TLS certificates |
| cffi | 2.0.0 | C FFI |
| cftime | 1.6.5 | NetCDF time |
| charset-normalizer | 3.4.4 | encoding |
| click | 8.3.1 | CLI |
| cloudpickle | 3.1.2 | serialization |
| colorama | 0.4.6 | terminal colors |
| contourpy | 1.3.3 | contouring |
| cryptography | 46.0.5 | crypto |
| cycler | 0.12.1 | matplotlib |
| dask | 2026.1.2 | parallel compute |
| deepdiff | 8.6.1 | object comparison |
| deprecation | 2.1.0 | deprecation warnings |
| fonttools | 4.61.1 | font handling |
| fsspec | 2026.2.0 | filesystem abstraction |
| geojson | 3.2.0 | GeoJSON |
| geopandas | 1.1.2 | geospatial |
| google-api-core | 2.30.0 | GCP |
| google-auth | 2.48.0 | GCP auth |
| google-cloud-core | 2.5.0 | GCP |
| google-cloud-storage | 3.9.0 | GCP storage |
| google-crc32c | 1.8.0 | CRC32C |
| google-resumable-media | 2.8.0 | GCP |
| googleapis-common-protos | 1.72.0 | GCP |
| highspy | 1.13.1 | HiGHS solver |
| idna | 3.11 | internationalization |
| iniconfig | 2.3.0 | pytest |
| jinja2 | 3.1.6 | templating |
| kiwisolver | 1.4.9 | constraint solving |
| levenshtein | 0.27.3 | string matching |
| linopy | 0.6.4 | optimization modeling |
| locket | 1.0.0 | file locking |
| markupsafe | 3.0.3 | safe strings |
| matplotlib | 3.10.8 | plotting |
| matpowercaseframes | 2.0.1 | MATPOWER parser |
| mypy-extensions | 1.1.0 | typing |
| narwhals | 2.17.0 | dataframe compat |
| netcdf4 | 1.7.3 | NetCDF I/O |
| networkx | 3.6.1 | graph algorithms |
| numexpr | 2.14.1 | numeric expressions |
| numpy | 2.3.5 | numerical computing |
| orderly-set | 5.5.0 | ordered sets |
| packaging | 25.0 | version parsing |
| pandapower | 3.4.0 | power system analysis |
| pandas | 2.3.3 | data frames |
| pandera | 0.26.1 | validation |
| partd | 1.4.2 | dask partitioning |
| pillow | 12.1.1 | imaging |
| plotly | 6.6.0 | interactive plots |
| pluggy | 1.6.0 | pytest plugins |
| polars | 1.38.1 | dataframes (Rust) |
| polars-runtime-32 | 1.38.1 | polars runtime |
| proto-plus | 1.27.1 | protobuf |
| protobuf | 6.33.5 | serialization |
| pyasn1 | 0.6.2 | ASN.1 |
| pyasn1-modules | 0.4.2 | ASN.1 |
| pycparser | 3.0 | C parser |
| pydantic | 2.12.5 | validation |
| pydantic-core | 2.41.5 | validation core |
| pydeck | 0.9.1 | map visualization |
| pygments | 2.19.2 | syntax highlighting |
| pyogrio | 0.12.1 | geospatial I/O |
| pyparsing | 3.3.2 | parsing |
| pyproj | 3.7.2 | projections |
| pypsa | 1.1.2 | power system analysis |
| pytest | 9.0.2 | testing |
| python-dateutil | 2.9.0.post0 | dates |
| pytz | 2026.1.post1 | timezones |
| pyyaml | 6.0.3 | YAML |
| rapidfuzz | 3.14.3 | string matching |
| requests | 2.32.5 | HTTP |
| rsa | 4.9.1 | crypto |
| scipy | 1.16.3 | scientific computing |
| seaborn | 0.13.2 | statistical plots |
| shapely | 2.1.2 | geometry |
| six | 1.17.0 | Python 2/3 compat |
| toolz | 1.1.0 | functional utils |
| tqdm | 4.67.3 | progress bars |
| typeguard | 4.5.1 | runtime type checks |
| typing-extensions | 4.15.0 | typing |
| typing-inspect | 0.9.0 | typing introspection |
| typing-inspection | 0.4.2 | typing introspection |
| tzdata | 2025.3 | timezone data |
| urllib3 | 2.6.3 | HTTP |
| validators | 0.35.0 | input validation |
| xarray | 2026.2.0 | labeled arrays |

Note: Some packages (google-*, polars, pandapower, matpowercaseframes) are pulled in by the evaluation project's additional dependencies, not by PyPSA itself.

## Implications

The dependency tree is fully enumerable and resolved via uv.lock. The 89-package count includes evaluation extras; PyPSA's own transitive closure is smaller. All packages are from PyPI with deterministic resolution.
