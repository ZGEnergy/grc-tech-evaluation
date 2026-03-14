---
test_id: F-9
tool: pypsa
dimension: supply_chain
network: N/A
status: pass
workaround_class: null
timestamp: 2026-03-13T12:00:00Z
protocol_version: v10
skill_version: v1
test_hash: 738f75e3
---

# F-9: Getting-Started Artifact Integrity

## Findings

### Official Examples

PyPSA provides 20+ example notebooks in `docs/examples/`:

- `minimal-example-pf.ipynb` — minimal power flow
- `example-1.ipynb` through `example-3.ipynb` — introductory tutorials
- `ac-dc-lopf.ipynb` — AC-DC optimal power flow
- `capacity-expansion-planning-single-node.ipynb` — CEP tutorial
- `unit-commitment.ipynb` — UC tutorial
- Plus domain-specific examples (BESS, CHP, biomass, etc.)

### Version Pinning

**Mixed.** The examples are version-coupled to the PyPSA release but
not explicitly pinned:

1. **No explicit version pin in examples**: The notebooks do not contain
   `pypsa==X.Y.Z` installation commands. They assume the user has PyPSA
   installed.

2. **Version-coupled via docs**: The documentation site (docs.pypsa.org)
   serves examples matching the latest release. Versioned documentation
   is available (e.g., docs for v1.0.0 vs v1.1.2).

3. **No mutable URLs**: Examples do not reference unversioned downloads,
   main branch tarballs, or mutable blob storage URLs. Data used in
   examples is either generated programmatically or bundled with the
   package.

4. **Dependency specification**: `pyproject.toml` uses lower bounds only
   (`pandas>=2.0`, `linopy>=0.6.1`), which means the example environment
   is not fully reproducible (see F-2 for details).

### Installation Instructions

The official README and docs specify:
```
pip install pypsa
```

This installs the latest version, not a pinned version. This is standard
practice for Python libraries but means getting-started artifacts are
not version-locked.

### PyPI Version Availability

All historical versions are available on PyPI, so users can pin to a
specific version:
```
pip install pypsa==1.1.2
```

### Assessment

The getting-started experience is clean and functional. Examples are
bundled with versioned documentation, avoiding the common pitfall of
examples that reference mutable URLs or unversioned downloads. The
lack of explicit version pinning in example notebooks is a minor concern
but is mitigated by the versioned documentation site.

## Recorded Metrics

- version_pinned: partially (docs versioned, examples not explicitly pinned)
- mutable_refs: none (no mutable URLs, no main-branch references in examples)
