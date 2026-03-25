---
tag: arch-quality
source_dimension: extensibility
source_test: B-6
tool: matpower
severity: medium
timestamp: 2026-03-24T00:00:00Z
---

# Observation: Dual-framework architecture (legacy + MP-Core) provides strong extensibility but adds complexity

## Finding

MATPOWER 8.1 ships two complete parallel architectures: a legacy procedural framework (stable since 1997, ~955 lines for DCPF path) and a new object-oriented MP-Core framework (introduced in 8.0, ~1,160 lines for the DC PF concrete classes alone, 208 class files in `lib/+mp/`). Both coexist and produce identical results. The MP-Core framework provides clean 4-layer separation (data model / network model / mathematical model / task) with a formal Extension API for adding custom elements and formulations without forking.

## Context

B-6 source code audit examined the DCPF solve path through both frameworks. The legacy path (`rundcpf` -> `runpf` -> `makeBdc` -> `dcpf`) is 6 files totaling ~955 lines. The new path (`run_pf` -> `mp.task_pf` -> `mp.net_model_dc` -> `mp.math_model_pf_dc`) spans 50+ classes. The Extension API (`mp.extension` base class) allows customizing any layer via subclassing. The core DC power flow solver (`dcpf.m`) is 46 lines -- a single sparse matrix backslash operation -- making it one of the most mathematically transparent implementations in this evaluation.

## Implications

For maturity assessment (E-dimension): The dual-framework design indicates active architectural investment but also transitional complexity. The legacy API's stability since 1997 is a strong maturity signal. The MP-Core framework's relative newness (2024) means less battle-testing.

For accessibility (D-dimension): New users must choose between two APIs. The legacy API is simpler and better documented (240+ page User's Manual), while the MP-Core API is more powerful but requires understanding OOP patterns and a less mature Developer Manual.
