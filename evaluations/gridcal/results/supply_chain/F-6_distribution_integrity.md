---
test_id: F-6
tool: gridcal
dimension: supply_chain
network: N/A
protocol_version: "v4"
status: pass
workaround_class: null
timestamp: 2026-03-06T05:00:00Z
---

# F-6: Air-Gap Installability

## Criteria

Verify that the tool and all dependencies can be installed in an air-gapped environment
with no runtime network access required for core analysis.

## Result: PASS

GridCal and all dependencies are installable from pre-downloaded wheel files. No runtime
network access is required for power flow, OPF, or any core analysis function.

### Evidence

- All 83 packages (direct + transitive) are available as wheels on PyPI and can be
  bundled with `pip download` or `uv pip compile` for offline installation
- No package requires post-install network fetches for functionality
- No license-server or activation mechanism exists in the open-source variant
- Core power flow and OPF operations confirmed functional without network connectivity

### Network-Adjacent Dependencies

- **websockets**: Listed as a dependency but not used in the core power flow or OPF
  execution path. It supports GridCal's optional GUI server mode. Does not phone home
  or require a network connection for batch analysis.
- **urllib3**: Transitive dependency (via other packages). Not invoked during analysis.

### Installation Procedure for Air-Gap

```bash
# On networked machine:
pip download veragridengine --dest ./wheels/
# Transfer ./wheels/ to air-gapped host
# On air-gapped machine:
pip install --no-index --find-links ./wheels/ veragridengine
```

All wheels are platform-specific for compiled deps (numpy, scipy, etc.) so the download
must target the same OS/architecture as the air-gapped host.
