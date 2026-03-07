---
test_id: F-9
tool: pandapower
dimension: supply_chain
network: N/A
protocol_version: "v4"
status: qualified_pass
workaround_class: null
wall_clock_seconds: null
peak_memory_mb: null
loc: null
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# F-9: Getting Started Integrity

## Result: QUALIFIED PASS

## Finding

pandapower's official getting-started page does not pin installation to a specific version,
and tutorial links point to mutable GitHub branches (master and develop) rather than tagged
releases. While PyPI releases are properly versioned, the onboarding documentation uses
unversioned install commands and mutable tutorial URLs.

## Evidence

### Installation commands (from pandapower.org/start/)

```bash
pip install pandapower[all]
```

- **No version pin.** The command installs whatever version is latest on PyPI.
- No mention of pinning to a specific version for reproducibility.

### Tutorial links

The getting-started page links to tutorial notebooks on GitHub. These links target
**mutable branches**, not release tags:

- **Master branch:** `https://github.com/panda-power/pandapower/blob/master/tutorials/`
- **Develop branch:** `https://github.com/e2nIEE/pandapower/blob/develop/tutorials/`
  (multiple tutorials including minimal_example, hosting_capacity, shortcircuit, tnep,
  time_series, plotly tutorials)

No tutorial links use versioned URLs such as:
`https://github.com/e2nIEE/pandapower/blob/v3.4.0/tutorials/`

### Binder links

The README contains a Binder link targeting master:
`https://mybinder.org/v2/gh/e2nIEE/pandapower/master?filepath=tutorials`

This launches an interactive environment with whatever is on `master`, which may not match
the latest PyPI release.

### Positive factors

- PyPI releases are versioned and tagged (v3.4.0, etc.).
- GitHub releases page has proper tags: <https://github.com/e2nIEE/pandapower/releases>
- The `pyproject.toml` pins all dependencies with `~=` operators.
- ReadTheDocs documentation is available at versioned URLs
  (e.g., `pandapower.readthedocs.io/en/v3.4.0/`).

## Implications

The lack of version pinning in install commands and the use of mutable branch URLs for
tutorials create a risk of version mismatch: users may install v3.4.0 from PyPI but follow
tutorial code from the develop branch that targets a future unreleased version. This is a
common pattern in open-source projects but represents a minor supply chain hygiene gap.

The qualification is mild -- the project does maintain proper versioned releases and tagged
documentation. The issue is limited to the getting-started page and tutorial links not
enforcing version alignment.
