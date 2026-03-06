# Observation: workaround-needed (Extensibility)

## Tool: PyPSA 1.1.2

### B-3: Branch Disconnection for Contingency Analysis

Workaround class: Stable

PyPSA has no dedicated branch enable/disable mechanism. To simulate branch removal for contingency analysis, the branch reactance is set to a very large value (`x = 1e10`), which effectively removes it from the power flow solution. The original value must be saved and restored after each contingency.

This is a stable workaround: it uses documented public attributes (`n.lines.x`, `n.transformers.x`) and relies on well-understood physical behavior (infinite reactance = zero flow). It will not break on version upgrades.

### B-7: Generator p_set Assignment for AC Feasibility Check

Workaround class: Stable (borderline not-a-workaround)

To check AC feasibility of a DC OPF dispatch, generator active power setpoints must be manually set via `n.generators.p_set = dispatch_value`. This is a standard PyPSA pattern for setting up power flow studies, not truly a workaround. The generator control types (Slack/PV/PQ) from MATPOWER import are correct for ACPF.
