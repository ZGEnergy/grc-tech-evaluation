# MATPOWER — Install & Smoke-Test Findings

**Date:** 2026-03-03
**Version resolved:** MATPOWER 8.1 (2025-07-12), GNU Octave 9.2.0
**Script:** [`../verify_install.m`](../verify_install.m)

## Summary

DCPF on IEEE 39-bus completed successfully with full system summary output.
The most detailed default output of any tool. Setup required workarounds
for non-standard release packaging.

## Findings

### [accessibility] install_matpower.m is interactive — unusable in scripts

MATPOWER ships an `install_matpower.m` script that prompts the user to
choose between three path configuration options. It calls `input()` which
blocks on stdin, making it unusable in non-interactive contexts (CI,
Docker, Octave batch mode). Our verify script had to manually `addpath`
five directories instead:

```matlab
addpath(fullfile(mp_root, 'lib'));
addpath(fullfile(mp_root, 'data'));
addpath(fullfile(mp_root, 'mips', 'lib'));
addpath(fullfile(mp_root, 'mp-opt-model', 'lib'));
addpath(fullfile(mp_root, 'mptest', 'lib'));
```

A user who doesn't know about `mips/` and `mp-opt-model/` will get
`'have_feature' undefined` errors at runtime. The dependency on these
sub-packages is not documented outside the interactive installer.

**Rubric relevance:** Accessibility (non-scriptable install),
Maturity (fragmented path setup).

### [supply_chain] Release is a zip, not a package manager install

MATPOWER is distributed as a GitHub release zip file (46 MB). There is
no `pkg install`, no `apt` package, no standard package manager path.
Setup requires `curl` + `unzip` + manual path configuration.

The SHA256 checksum is not published alongside the release — we had to
compute it ourselves. The release tarball mentioned in some docs
(`matpower-8.1.tar.gz`) does not exist; only `matpower8.1.zip` is
published.

**Rubric relevance:** Supply Chain (no package manager, no published
checksums), Accessibility (manual setup).

### [accessibility] Richest default DCPF output of any tool

`rundcpf` prints a complete system summary by default:

- System overview (buses, generators, loads, branches, areas)
- Voltage magnitude and angle at every bus
- Generation and load at every bus
- Branch flows (P and Q, both directions) for all 46 branches
- Total losses summary

No other tool produces this level of output without explicit
post-processing. For interactive exploration this is excellent; for
programmatic use the output would need to be parsed from structs.

### [maturity] The reference implementation

MATPOWER is the canonical implementation that all other tools validate
against. Its `.m` file format is the de facto standard for sharing power
system test cases. Every other tool in this evaluation either reads `.m`
files natively or needs a converter to do so.

The code is stable, well-tested, and has been used in academic research
for 25+ years. The branch count (46), bus count (39), and flow values
match the published IEEE 39-bus reference data exactly.

### [maturity] Sub-package architecture adds setup complexity

MATPOWER 8.1 has been refactored into sub-packages (MIPS, MP-OPT-MODEL,
MPTEST) each with their own `lib/` directory. This is good software
architecture but means the path setup requires knowledge of the internal
structure. The `have_feature` function lives in `mp-opt-model/lib/` —
without it, `mpoption` fails, which breaks all solvers.

### [gate] DCPF passes

39 buses, 46 branches, total generation matches total load (6254.23 MW),
zero losses (as expected for DC). Reference-quality results.
