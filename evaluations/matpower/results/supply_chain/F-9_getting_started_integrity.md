---
test_id: F-9
tool: matpower
dimension: supply_chain
network: N/A
protocol_version: "v4"
status: informational
workaround_class: null
timestamp: "2026-03-06T14:00:00Z"
---

# F-9: Getting Started Integrity

## Question

Are official examples and getting-started materials pinned to a specific release?
Are there mutable URLs or instructions that could break or change silently?

## Official Documentation Sources

| Source | URL / Location | Pinned? |
|--------|---------------|---------|
| User's Manual (PDF) | Bundled in release zip: `docs/MATPOWER-manual.pdf` | YES — ships with version |
| Sphinx docs (web) | `https://matpower.org/docs/` | PARTIAL — tracks latest |
| GitHub README | `https://github.com/MATPOWER/matpower` | NO — mutable |
| MOST User's Manual | Bundled in release zip: `most/docs/` | YES — ships with version |
| Tech Notes (PDFs) | Bundled in release zip: `docs/TN*.pdf` | YES — ships with version |

## Example Scripts

All example scripts are **bundled in the release zip** and versioned:

| Location | Files | Version-Pinned? |
|----------|-------|----------------|
| `examples/cpf_example.m` | 1 | YES |
| `most/examples/most_ex*.m` | 7 | YES |
| `mips/examples/mips_example*.m` | 2 | YES |
| `mp-opt-model/examples/*.m` | 10 | YES |

No examples reference external URLs, download data at runtime, or depend on
web services.

## Mutable URL Audit

| URL | Context | Risk |
|-----|---------|------|
| `https://matpower.org` | Referenced in source headers | LOW — project website, could change |
| `https://github.com/MATPOWER/matpower` | README, issues | LOW — standard GitHub URL |
| `https://matpower.org/docs/` | Sphinx documentation | MODERATE — tracks latest, not versioned |
| Release download URL | `github.com/.../releases/download/8.1/matpower8.1.zip` | LOW — GitHub preserves release assets |

## Version Drift Risk

1. **Web documentation (`matpower.org/docs/`):** Not versioned per release. As
   the project evolves, web docs may describe features not in the user's installed
   version. The Sphinx docs currently note "not yet available" for the web User's
   Manual, directing users to the bundled PDF.

2. **GitHub README:** Mutable, but changes are tracked in Git history.

3. **Bundled documentation:** The PDFs and example scripts in the release zip
   are frozen at release time. This is the most reliable reference.

## Assessment

MATPOWER's getting-started materials are predominantly **bundled with the release**,
which is the gold standard for version integrity. The PDF manual, all tech notes,
and all example scripts ship in the zip file and match the installed version.

The main gap is the web-based Sphinx documentation at `matpower.org/docs/`, which
tracks the latest development version rather than specific releases. However, the
project mitigates this by explicitly directing users to the bundled PDF manual.

No mutable URLs in example code. No runtime downloads. No external data dependencies.

| Check | Status |
|-------|--------|
| Examples pinned to release | YES (bundled in zip) |
| Documentation pinned to release | YES (PDF in zip); web docs track latest |
| Mutable URLs in examples | NONE |
| Runtime data downloads | NONE |
| External service dependencies | NONE |
