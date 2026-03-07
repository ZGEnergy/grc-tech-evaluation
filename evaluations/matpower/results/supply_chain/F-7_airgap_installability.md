---
test_id: F-7
tool: matpower
dimension: supply_chain
network: N/A
protocol_version: "v4"
status: pass
workaround_class: null
timestamp: "2026-03-06T14:00:00Z"
---

# F-7: Air-Gap Installability

## Question

Can MATPOWER + GNU Octave be installed and operated in a fully offline
(air-gapped) environment with no network access?

## Analysis

### MATPOWER Installation

**Fully air-gap compatible.**

1. Download `matpower8.1.zip` from GitHub on a connected machine.
2. Transfer to air-gapped environment via USB/media.
3. Unzip and add to Octave path — no network access required.
4. `install_matpower.m` modifies the local Octave path only (no downloads).

MATPOWER has **zero runtime network dependencies**:
- No license server check
- No telemetry or analytics
- No package manager resolution
- No dynamic dependency fetching
- No update checks

### GNU Octave Installation

**Air-gap compatible with standard OS packaging.**

- Octave is available in all major Linux distribution repositories (apt, yum, dnf).
- For air-gapped Linux: pre-download `.deb`/`.rpm` packages and dependencies.
- For Windows: standalone Octave installer (MSI/ZIP) is self-contained.
- For macOS: Homebrew bottle or standalone .app bundle.

Octave includes GLPK (LP/MILP solver) bundled, so no additional solver
installation is needed for basic functionality.

### Optional Solvers

| Solver | Air-Gap Status | Notes |
|--------|---------------|-------|
| MIPS | Bundled — no action needed | Part of MATPOWER zip |
| GLPK | Bundled with Octave — no action needed | Available immediately |
| IPOPT | Requires separate build/download | MEX file must be compiled or pre-built |
| OSQP | Requires separate build/download | MEX file must be compiled or pre-built |
| HiGHS | Requires separate installation | System package or build from source |

Core MATPOWER functionality (PF, OPF, MOST) works with MIPS + GLPK alone.

## Verification

Our devcontainer setup demonstrates offline-compatible installation:

```bash
# setup.sh downloads zip once, then everything is local
curl -L -o matpower8.1.zip "$MATPOWER_URL"
sha256sum -c -  # verify integrity
unzip -q matpower8.1.zip
# No further network access needed
```

After initial download, all operations are local:

```bash
octave --eval "addpath(genpath('matpower8.1')); runpf('case9')"
```

## Assessment

**PASS.** MATPOWER is exceptionally well-suited for air-gapped deployment.
The entire tool is a zip file of .m text files with no compiled dependencies,
no runtime network calls, and no license verification. Combined with GNU
Octave (which can be pre-packaged), the complete stack can operate with
zero network connectivity.

This is a significant advantage for secure/classified computing environments
where network isolation is mandatory.
