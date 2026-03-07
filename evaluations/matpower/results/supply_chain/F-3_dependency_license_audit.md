---
test_id: F-3
tool: matpower
dimension: supply_chain
network: N/A
protocol_version: "v4"
status: pass
workaround_class: null
timestamp: "2026-03-06T14:00:00Z"
---

# F-3: Dependency License Audit

## Methodology

Examined LICENSE files in each sub-package directory within
`/workspace/evaluations/matpower/matpower8.1/`.

## License Inventory

### Core Sub-Packages

| Package | License File | License Type | Copyright Holder |
|---------|-------------|-------------|------------------|
| MATPOWER | `LICENSE` | BSD 3-Clause | PSERC, 1996-2025 |
| MIPS | `mips/LICENSE` | BSD 3-Clause | PSERC, 1996-2025 |
| MP-Opt-Model | `mp-opt-model/LICENSE` | BSD 3-Clause | PSERC, 2004-2025 |
| MOST | `most/LICENSE` | BSD 3-Clause | PSERC, 1996-2025 |
| MPTEST | `mptest/LICENSE` | BSD 3-Clause | PSERC, 1996-2025 |

### Extras

| Package | License File | License Type | Copyright Holder |
|---------|-------------|-------------|------------------|
| Simulink MATPOWER | `extras/simulink_matpower/LICENSE` | BSD 3-Clause-like | ETH Zurich, 2023 |
| SDP_PF | `extras/sdp_pf/LICENSE` | BSD 3-Clause | PSERC, 2013-2020 |
| SynGrid | `extras/syngrid/LICENSE` | BSD 3-Clause | Individual contributors, 2007-2024 |

### Runtime Environment

| Component | License | Notes |
|-----------|---------|-------|
| GNU Octave | GPL-3.0 | Octave itself is GPL, but running MATPOWER code inside Octave does not make MATPOWER GPL (analogous to running BSD code on Linux) |
| MATLAB | Commercial (MathWorks) | Requires paid license |
| GLPK | GPL-3.0 | Bundled with Octave; used as external solver via function calls |

## GPL Interaction Analysis

GNU Octave and GLPK are GPL-3.0. However, MATPOWER interacts with these through
function calls (Octave's built-in interpreter and GLPK's `glpk()` function).
MATPOWER does not link against GPL libraries at compile time — it is interpreted
code calling interpreter-provided functions. This is the standard "application
running on a GPL platform" pattern and does not trigger copyleft obligations
for MATPOWER code.

## Copyleft Risk

**None identified.** All MATPOWER code and sub-packages are BSD 3-Clause.
The GPL components (Octave, GLPK) are runtime dependencies accessed through
standard interpreter interfaces, not linked libraries.

## Assessment

**PASS.** Entire MATPOWER distribution is BSD 3-Clause. No copyleft dependencies
in the code itself. Runtime GPL dependencies (Octave, GLPK) follow the standard
"application on GPL platform" pattern with no license contamination risk.
