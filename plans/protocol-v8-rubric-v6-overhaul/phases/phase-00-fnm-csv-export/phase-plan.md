# Purpose

The evaluation framework's Suite G (FNM ingestion) tests currently force every tool through a MATPOWER-format input path: a `.mat` file produced by `psse2mpc`, which merges branches and transformers into a single table, drops several PSS/E record types entirely, and requires tools to reverse-engineer the branch/transformer distinction from the tap ratio column. This creates a systematic bias — tools that can ingest richer formats are penalized for MATPOWER's lossy representation, and tools without a MATPOWER/pypower import path must build one as a workaround.

Phase 0 eliminates this bias by materializing the intermediate-format CSVs that the schema (`data/fnm/intermediate/schemas/`) already defines. The export pipeline reads the cleaned MATPOWER case (`data/fnm/reference/cleaned/fnm_main_island.mat`), applies the cleaning steps documented in `summary_cleaning.json`, writes one CSV per non-empty PSS/E record type with the exact column names from the JSON Schema files, and produces a baseMVA sidecar metadata file. Critically, the CSVs preserve the branch/transformer distinction as separate tables, pre-convert MATPOWER's tap=0.0 convention to the PSS/E-standard 1.0, and encode bus types using the PSS/E 1/2/3/4 integer codes.

The downstream consumer of these outputs is Phase 1 (Protocol & Rubric Edits), which will update the v8 protocol to reference the intermediate CSVs as the primary G-FNM input path, with the cleaned MATPOWER `.m` as a documented fallback. Before that can happen, the DCPF reference solution must be validated as reproducible from the new CSV path — otherwise the protocol change would break the evaluation pipeline. This phase therefore also updates `dcpf_reference.py` to accept separate branch and transformer CSV tables and validates that the DCPF solution computed from the intermediate CSVs matches the existing reference to within floating-point tolerance.

---

# What This Phase Produces

**Output:** A complete set of intermediate-format CSV files committed to `data/fnm/reference/cleaned/intermediate/`, one per non-empty PSS/E v31 record type (bus, load, generator, branch, transformer, area, zone, switched_shunt — 8 CSVs based on the intermediate manifest). A `manifest.json` sidecar containing baseMVA, source provenance, record counts, and cleaning step metadata. An updated `dcpf_reference.py` that can consume separate branch and transformer CSVs (in addition to the existing merged-branch path). Validation evidence that the DCPF reference solution is bit-reproducible from the new CSV path.

**Downstream consumer:** Phase 1 (Protocol & Rubric Edits) references the intermediate CSV paths in the v8 protocol. Phase 2 (Skill Machinery Updates) references them in code-evaluator prompts for G-FNM test implementation.

---

# Design Decisions

## Separate branch and transformer CSVs rather than a merged table

The intermediate schema defines `branch` and `transformer` as separate tables with different column sets (branch has 24 columns; transformer has 83). MATPOWER merges these into a single 13-column `branch` matrix, losing transformer-specific fields (winding MVA bases, impedance correction tables, multi-winding topology). The CSVs preserve the PSS/E distinction so tools can map directly to their native transformer models without reverse-engineering from tap ratios.

The `dcpf_reference.py` update must handle both the legacy merged path (for backward compatibility with existing tests) and the new separate-table path. The approach is a new `--transformer-csv` optional argument: when provided, branches and transformers are loaded from separate files; when omitted, the existing merged-branch loading logic applies unchanged.

## baseMVA as sidecar metadata, not a CSV column

baseMVA is a scalar system-level parameter (100.0 for this network), not a per-record attribute. Embedding it as a column in every CSV would be redundant and error-prone. Instead, it is stored in the `manifest.json` sidecar file alongside record counts and provenance. The `dcpf_reference.py` update reads baseMVA from the manifest when using the intermediate CSV path, or from the `--base-mva` CLI argument as before.

## tap=0 pre-conversion to 1.0 in the export pipeline

MATPOWER uses tap=0.0 to mean "nominal tap ratio" (equivalent to 1.0). This convention is a frequent source of division-by-zero bugs in tools that interpret 0.0 literally. The export pipeline converts all tap=0.0 values to 1.0 at export time, so downstream consumers never encounter this ambiguity. The `dcpf_reference.py` already performs this normalization internally; with pre-converted CSVs the normalization becomes a no-op safety check.

## Explicit `is_transformer` column in the branch CSV

Even within the branch table (which contains only non-transformer elements after splitting), MATPOWER's merged format can contain entries with tap != 1.0 that are actually phase-shifting branches, not classical transformers. The export pipeline does not add an `is_transformer` column to the branch CSV — the table-level separation (branch vs transformer file) is the distinction. Elements in `branch.csv` are lines; elements in `transformer.csv` are transformers.

## Exclusion filtering applied at export time

The intermediate CSVs represent the main-island-filtered, cleaned network — the same network described in `summary_cleaning.json`. Buses in `excluded_buses.json` (2,445 buses from non-main islands and isolated nodes) are excluded from the exported CSVs. This means the CSVs contain only the 27,862 main-island buses and their connected elements, matching the DCPF reference solution's input set exactly. Tools ingesting from these CSVs do not need to perform their own island filtering.

## JSON Schema validation of exported CSVs

The `data/fnm/intermediate/schemas/` directory contains JSON Schema Draft 2020-12 definitions for every table. The export pipeline validates each CSV against its schema before writing, ensuring column names, types, and constraints match the schema exactly. This catches drift between the export code and the schema specification.

---

# Deliverables

### 1. Export Pipeline Script
- **Description:** A Python script (`data/fnm/scripts/export_intermediate_csvs.py`) that reads the cleaned MATPOWER case file (`fnm_main_island.mat`), splits branches from transformers, applies tap=0 to 1.0 conversion, filters to main-island buses, and writes one CSV per non-empty PSS/E record type to `data/fnm/reference/cleaned/intermediate/`. Also writes `manifest.json` with baseMVA, provenance, and record counts. Validates each CSV against the corresponding JSON Schema.
- **Estimated tests:** 12
- **Dependencies:** None (uses existing `.mat` file, schemas, and cleaning metadata as inputs)

### 2. Intermediate CSV Materialization
- **Description:** Run the export pipeline inside the devcontainer to produce the actual CSV files and manifest. Commit the output files to `data/fnm/reference/cleaned/intermediate/`. Verify record counts match the intermediate manifest expectations and the cleaning summary. This deliverable is the execution of Deliverable 1 — the committed artifacts, not the script.
- **Estimated tests:** 8
- **Dependencies:** 1

### 3. dcpf_reference.py Separate-Table Support
- **Description:** Update `dcpf_reference.py` to accept an optional `--transformer-csv` argument. When provided, the script loads branches from `--branch-csv` and transformers from `--transformer-csv` separately, then combines them for B-matrix construction. The existing merged-branch path remains the default when `--transformer-csv` is omitted. Also add a `--manifest` argument to read baseMVA from the sidecar manifest instead of requiring `--base-mva`.
- **Estimated tests:** 10
- **Dependencies:** 1

### 4. DCPF Reference Reproducibility Validation
- **Description:** Run `dcpf_reference.py` with the new intermediate CSVs (separate branch + transformer tables, baseMVA from manifest) and compare the output against the existing reference in `data/fnm/reference/dcpf/`. Bus angles must match to within 0.001 degrees, branch flows to within 0.1 MW. This validates that the format change is lossless for the DCPF computation. The validation script produces a comparison report.
- **Estimated tests:** 8
- **Dependencies:** 2, 3

---

# Deliverable Dependencies

| # | Deliverable | Depends On | Enables |
|---|-------------|-----------|---------|
| 1 | Export Pipeline Script | — | 2, 3 |
| 2 | Intermediate CSV Materialization | 1 | 4 |
| 3 | dcpf_reference.py Separate-Table Support | 1 | 4 |
| 4 | DCPF Reference Reproducibility Validation | 2, 3 | — |

**Implementation tiers** (deliverables within a tier have no mutual dependencies):

- **Tier 1:** 1. Export Pipeline Script
- **Tier 2:** 2. Intermediate CSV Materialization, 3. dcpf_reference.py Separate-Table Support
- **Tier 3:** 4. DCPF Reference Reproducibility Validation

---

# Open Questions

None — all decisions resolved.
