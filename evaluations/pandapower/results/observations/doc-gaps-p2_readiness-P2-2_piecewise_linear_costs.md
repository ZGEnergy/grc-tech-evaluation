---
tag: doc-gaps
source_dimension: p2_readiness
source_test: P2-2
tool: pandapower
severity: low
timestamp: 2026-03-06T00:00:00Z
---

# Observation: PWL cost format differs from MATPOWER convention

## Finding

pandapower's `create_pwl_cost` uses the format `[[p_start, p_end, marginal_cost], ...]` which differs from MATPOWER's `[[p, c], ...]` (power-cost pairs) convention. While the pandapower format is documented, users familiar with MATPOWER may initially use the wrong format, leading to ValueError exceptions ("not enough values to unpack").

## Context

Discovered during P2-2 PWL cost testing. The initial implementation used `[[p, c]]` pairs (MATPOWER convention) and received a ValueError. The correct format was found in the `create_pwl_cost` docstring.

## Implications

The documentation is adequate (docstring includes examples), but the format divergence from MATPOWER may trip up users. This is a minor accessibility finding. The error message itself ("not enough values to unpack") does not indicate the correct format, which adds friction.
