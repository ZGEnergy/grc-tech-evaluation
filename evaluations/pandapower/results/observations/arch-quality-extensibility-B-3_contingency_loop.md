---
tag: arch-quality
source_dimension: extensibility
source_test: B-3
tool: pandapower
severity: low
timestamp: 2026-03-06T00:00:00Z
---

# Observation: Efficient in-place branch switching for contingency analysis

## Finding

pandapower's DataFrame-based data model enables efficient N-1 contingency analysis via in-place branch switching (`net.line.at[idx, "in_service"] = False`). No model reconstruction, re-parsing, or cloning is needed between contingency cases. The 46-case N-1 sweep completed in 0.307 s (6.7 ms per case) on the IEEE 39-bus network.

## Context

B-3 tested full N-1 DCPF contingency screening. The workflow was: disable branch, solve DCPF, collect results, restore branch. This worked without any workarounds and with minimal overhead. The `in_service` flag is a documented, standard part of pandapower's data model.

## Implications

This is a positive finding for both Extensibility and Scalability. The in-place modification pattern is efficient and idiomatic. The per-case overhead (6.7 ms) is dominated by the DCPF solve itself, not by model manipulation, which bodes well for larger contingency sweeps.
