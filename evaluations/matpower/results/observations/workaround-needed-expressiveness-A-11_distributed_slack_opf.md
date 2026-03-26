---
tag: workaround-needed
source_dimension: expressiveness
source_test: A-11
tool: matpower
severity: medium
timestamp: 2026-03-24T00:00:00Z
---

# Observation: Distributed slack OPF requires post-processing via makePTDF

## Finding

MATPOWER's OPF formulation uses a single slack bus internally and does not support distributed slack in the optimization itself. Distributed slack LMPs are achievable only as a post-processing step using `makePTDF(baseMVA, bus, branch, slack_weights)`, which accepts a documented custom slack distribution vector. The workaround is clean (documented public API, 3 lines of code) and produces correct results for DC OPF (dispatch unchanged, LMPs shift by uniform constant).

## Context

Test A-11 required distributed slack DC OPF with settable weights. Three weight configurations (load-proportional, generation-proportional, equal) were tested successfully. The LMP shift is perfectly uniform (std = 0.0), confirming that in lossless DC OPF, distributed slack only changes the reference point. The `makePTDF` function's slack distribution parameter is documented in the MATPOWER reference manual.

## Implications

- **Extensibility:** The workaround is stable (documented API) but means that distributed slack cannot be embedded in more complex formulations (e.g., lossy DC OPF where loss factors would depend on the slack distribution). Open issue #136 on GitHub tracks this limitation.
- **Accessibility:** The `makePTDF` function's slack vector parameter is documented but not prominently featured in examples or tutorials. Users would need to read the function reference to discover it.
