---
test_id: F-9
tool: pandapower
dimension: supply_chain
network: N/A
status: informational
workaround_class: null
timestamp: 2026-03-13T00:00:00Z
protocol_version: "v10"
skill_version: "v1"
test_hash: "64229977"
---

# F-9: Getting-Started Artifact Integrity

## Summary

pandapower's documentation supports version-pinned URLs via ReadTheDocs, and tutorials
are part of the versioned Git repository. However, the primary website and installation
instructions do not pin versions in `pip install` commands, and tutorial notebooks are
not shipped inside the installed package. **Grade: B+.**

## Findings

### Documentation Versioning

- **ReadTheDocs** hosts documentation at `pandapower.readthedocs.io` with versioned
  URLs (e.g., `/en/v3.4.0/`). Users can pin to a specific release.
- The **default "latest" URL** (`/en/latest/`) tracks the development branch, which
  is mutable. This is the standard ReadTheDocs convention.
- The documentation header correctly displays the version number (3.4.0).

### Installation Instructions

The official website (`pandapower.org`) and documentation recommend:

```
pip install pandapower
```

This command installs the latest release without pinning a version. No `pip install
pandapower==3.4.0` form is shown in official guides. This is standard practice for
most Python packages but means a user following the guide at different times may get
different versions.

### Tutorial Notebooks

- **72 tutorial notebooks** are maintained in the `tutorials/` directory of the GitHub
  repository, covering power flow, OPF, state estimation, short-circuit analysis,
  protection, plotting, and more.
- Tutorials are **part of the versioned repository** — they are included in tagged
  releases (e.g., `v3.4.0`) and can be accessed at a specific Git tag.
- Tutorials are **not shipped inside the installed pip package**. Users must clone the
  repository or download from GitHub to access them.
- The `[tutorials]` optional extra installs runtime dependencies for notebooks
  (juliacall, seaborn, jupyter) but does not install the notebooks themselves.

### Mutable URL Concerns

| Resource                        | Pinnable? | Notes                          |
|---------------------------------|-----------|--------------------------------|
| ReadTheDocs docs                | Yes       | `/en/v3.4.0/` URLs work       |
| PyPI package                    | Yes       | `==3.4.0` syntax available     |
| GitHub tutorials                | Yes       | Via tag checkout                |
| pandapower.org website          | No        | No versioned URLs              |
| GitHub `develop` branch links   | No        | Mutable, used in some docs     |

### Built-in Example Networks

pandapower ships built-in example networks accessible via `pp.networks.case9()`,
`pp.networks.create_cigre_network_mv()`, etc. These are part of the installed
package and are version-locked to the release. This partially compensates for
tutorials not being shipped in the package.

## Risks

- **Low risk:** Unversioned `pip install` command in docs could lead to version
  mismatch if tutorials reference APIs that change between releases. Mitigated by
  pandapower's stable API and semantic versioning.
- **Low risk:** Tutorials must be obtained from GitHub rather than `pip install`,
  adding a step for offline users. Mitigated by built-in example networks.
