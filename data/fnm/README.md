# FNM Data Directory

This directory contains artifacts related to the Full Network Model (FNM) ingestion
pipeline. The FNM data itself is NDA-restricted and **must never be committed to version
control**.

## Directory Layout

```
data/fnm/
├── manifest.json          # Machine-readable list of expected FNM source files
├── .gitignore             # Blocks all FNM data files from version control
├── README.md              # This file
├── intermediate/          # Parser output (Parquet, intermediate formats)
├── reference/             # Phase 3 verification / reference solution datasets
├── docs/                  # Reference documentation for PSS/E record types, supplemental CSVs
└── scripts/               # Python modules for parsing, validation, and manifest I/O
```

## NDA Restrictions

FNM source files (PSS/E RAW files and supplemental CSVs) are provided under NDA.
They must not be committed, shared publicly, or stored in any unencrypted location outside
approved infrastructure.

The `.gitignore` in this directory blocks all data file extensions (`*.raw`, `*.csv`,
`*.parquet`, `*.m`) and the `intermediate/` and `reference/` directories from being tracked.

## FNM_PATH Environment Variable

All FNM-dependent code is gated by the `FNM_PATH` environment variable. Set it to the
directory containing the FNM source files:

```bash
export FNM_PATH=/path/to/fnm/source/files
```

When `FNM_PATH` is not set, FNM-dependent tests are skipped and parsers will raise errors
if invoked directly.

## Obtaining FNM Source Files

FNM source files must be obtained through the ISO's authorized distribution channels.
Contact the data engineering team for access. The `manifest.json` file lists all expected
source files with descriptions.

## Manifest

The `manifest.json` file enumerates every expected FNM source file. Use the
`scripts/manifest_io.py` module to load, validate, and update the manifest
programmatically rather than editing the JSON directly.
