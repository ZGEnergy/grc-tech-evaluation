# Report Update Process

This runbook describes how to refresh the report site when a new version of the
test protocol is executed.

## Goal

Produce a report update that:

- reflects the latest protocol outputs
- keeps `report/data/*.json` consistent with source material
- rebuilds the Docusaurus site successfully
- passes strict validation before merge

## Current State

The report site is only partially automated.

- Site build and deployment are automated.
- The translation from protocol outputs into `report/data/*.json` is still
  manual.
- Narrative MDX pages are still manually maintained.

## Source of Truth

Refresh the report from these upstream artifacts:

- `report/selection-report-v4.md` or its successor for grades, rankings, risks,
  and head-to-head conclusions
- `sweep-data/<protocol-version>/aggregation/comparison-matrices.md` for
  per-test outcomes
- `sweep-data/<protocol-version>/aggregation/themes.md` for cross-cutting themes
- `sweep-data/<protocol-version>/probes/*/probe-*.md` for probe summaries
- `sweep-data/<protocol-version>/per-tool/*/findings.md` for tool-specific
  findings
- synthesis files, if available, for tool profiles and narrative updates

## Update Steps

1. Run the new protocol and finish the upstream evaluation artifacts.

2. Update the report data layer in `report/data/`.
   Refresh:
   - `grades.json`
   - `sensitivity.json`
   - `risk-register.json`
   - `head-to-head.json`
   - `sweep-themes.json`
   - `probe-results.json`
   - `tool-profiles.json`
   - `test-results.json`

3. Update `_provenance` fields in each JSON file.
   Ensure source paths, extracted dates, and any line references match the new
   protocol inputs.

4. Update narrative pages that summarize or interpret the refreshed data.
   Most likely:
   - `report/docs/results/index.mdx`
   - `report/docs/results/probe-results.mdx`
   - `report/docs/results/sweep-findings.mdx`
   - criterion pages under `report/docs/results/`
   - `report/docs/results/head-to-head.mdx`
   - `report/docs/tools-evaluated.mdx`
   - `report/selection-report-v4.md` or its successor

5. Rebuild the site locally.

   ```bash
   cd report
   make build
   ```

6. Run strict validation.

   ```bash
   cd report
   make validate
   ```

7. Run editorial review before merge.
   Use `report/REVIEW_CHECKLIST.md` for final manual review.

8. Merge the change to `main`.
   GitHub Pages deployment is handled by `.github/workflows/deploy-report.yml`.

## Validation Expectations

Before opening or merging a PR:

- `make validate` passes
- internal links and anchors are clean
- no missing static assets remain
- content validation passes
- the local preview renders the updated pages correctly

## Deployment

On merge to `main`, the GitHub Pages workflow:

- installs Node and Python dependencies
- runs `cd report && make validate`
- uploads `report/build`
- deploys the built site to GitHub Pages
- runs the smoke test against the deployed URL

## Known Gap

There is no scripted pipeline today that regenerates `report/data/*.json`
directly from protocol artifacts. The JSON refresh step remains manual and
should be treated as the main source of update risk until a generator is added.
