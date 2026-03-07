---
test_id: F-8
tool: gridcal
dimension: supply_chain
network: N/A
protocol_version: "v4"
status: qualified_pass
workaround_class: null
timestamp: 2026-03-06T05:00:00Z
---

# F-8: Getting-Started Integrity

## Criteria

Assess whether official getting-started examples are version-pinned, tested, and
produce correct results with the evaluated version.

## Result: QUALIFIED PASS

Official examples function but have friction from the GridCal-to-VeraGrid rename and
lack version pinning.

### Evidence

- **ReadTheDocs examples**: Track the `master`/`stable` branch, not a specific release
  version. Examples may drift from the installed package version.
- **Rename friction**: The package was renamed from `GridCal` to `VeraGridEngine`
  (`veragridengine` on PyPI). Some examples and documentation still reference old import
  paths (`import GridCal` vs `import GridCal` -- the internal module name was preserved
  but the package name changed). This creates confusion for new users following older
  tutorials.
- **GitHub examples directory**: Contains runnable scripts that work with the current
  version, but no CI job validates them against each release.
- **API tutorials**: The core API (`MultiCircuit`, `PowerFlowOptions`, `PowerFlowDriver`)
  is stable and examples using these work correctly with v5.6.28.

### Qualification Reason

- Examples are not pinned to specific versions
- No automated testing of examples in CI
- Rename creates onboarding friction (users may install wrong package or use wrong
  import paths from older guides)
- Once past the naming confusion, the core workflow examples produce correct results
