---
tag: doc-gaps
source_dimension: extensibility
source_test: B-1
tool: pandapower
severity: medium
timestamp: 2026-03-06T00:00:00Z
---

# Observation: OPF constraint dual values undocumented in public API

## Finding

pandapower's `net.res_line` DataFrame does not expose shadow prices (dual values) for line flow constraints after OPF. Duals are only accessible via the private `net._ppc["branch"]` array at PYPOWER column index 17 (MU_SF) and 18 (MU_ST). This column layout is not documented in pandapower's own documentation and requires knowledge of PYPOWER internals.

## Context

During B-1 (custom constraints), per-line flow limits were set via the documented `max_i_ka` attribute. The constraint was binding (100% loading, objective increased by 6.9%). However, extracting the shadow price required:
1. Knowing that `net._ppc` exists after OPF (private attribute)
2. Knowing PYPOWER's branch column layout (MU_SF=17, MU_ST=18)
3. Understanding the pandapower-to-PYPOWER index mapping via `net._pd2ppc_lookups["branch"]`

None of this is documented in pandapower's user-facing documentation.

## Implications

This affects the Accessibility audit (documentation completeness) and Extensibility grade. Users who need constraint duals -- a common requirement in market analysis -- must read PYPOWER source code. The workaround is classified as fragile because it relies on private attributes.
