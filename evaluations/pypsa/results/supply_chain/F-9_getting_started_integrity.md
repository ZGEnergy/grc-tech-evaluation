---
test_id: F-9
tool: pypsa
dimension: supply_chain
network: N/A
protocol_version: v11
skill_version: v2
test_hash: 738f75e3
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
loc: null
solver: null
timestamp: 2026-03-24T14:00:00Z
---

# F-9: Getting-Started Artifact Integrity

## Result: PASS

## Finding

PyPSA's getting-started examples are bundled with versioned documentation, use no mutable URLs, and generate data programmatically rather than fetching from external sources. Examples are version-coupled to documentation releases. No mutable download references found.

## Evidence

### Official Examples

PyPSA provides 20+ example notebooks in `docs/examples/`:
- `minimal-example-pf.ipynb` — minimal power flow
- `example-1.ipynb` through `example-3.ipynb` — introductory tutorials
- `ac-dc-lopf.ipynb` — AC-DC optimal power flow
- `capacity-expansion-planning-single-node.ipynb` — CEP tutorial
- `unit-commitment.ipynb` — UC tutorial
- Plus domain-specific examples (BESS, CHP, biomass, etc.)

### Version Pinning Assessment

| Aspect | Status | Notes |
|--------|--------|-------|
| Explicit version pins in examples | No | Notebooks assume PyPSA is pre-installed |
| Versioned documentation | Yes | docs.pypsa.org serves version-specific docs |
| Mutable URLs | None | No main-branch tarballs or blob storage links |
| Data sourcing | Programmatic | Examples generate data inline, no external downloads |
| PyPI version availability | Yes | All historical versions available for pinning |

### Installation Instructions

Official README and docs specify:
```
pip install pypsa
```
This installs the latest version. Users can pin explicitly:
```
pip install pypsa==1.1.2
```

### Dependency Reproducibility

`pyproject.toml` uses lower bounds only (`pandas>=2.0`, `linopy>=0.6.1`) without upper bounds. This means the example environment is not fully reproducible across time — a known minor concern (see F-2). The `uv.lock` file in the evaluation environment provides a fully pinned snapshot for reproducibility.

### Flags

- No unversioned archive downloads
- No mutable blob storage URLs
- No `main` branch references in example code
- No external API calls in getting-started path

## Implications

Getting-started artifacts are clean and self-contained. The lack of explicit version pinning in notebooks is standard Python library practice and is mitigated by versioned documentation. No supply chain integrity risk from example artifacts.
