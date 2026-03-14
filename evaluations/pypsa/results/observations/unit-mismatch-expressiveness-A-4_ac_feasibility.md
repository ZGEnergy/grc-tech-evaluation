---
tag: unit-mismatch
source_dimension: expressiveness
source_test: A-4
tool: pypsa
severity: medium
timestamp: 2026-03-14T00:30:00Z
---

# Observation: DC vs AC transformer susceptance convention mismatch

## Finding

The shared MATPOWER loader's transformer susceptance patch (`b = 1/x` for
DC convention) causes AC power flow to diverge completely (NR error grows
to 10^41). The DC and AC power flow paths require different transformer
model parameterizations within PyPSA.

## Context

During A-4 (AC feasibility check on DC OPF dispatch), the initial
implementation used the shared `load_pypsa()` loader for both DC OPF and
AC PF. The DC OPF solved correctly, but the subsequent AC PF diverged
after 100 NR iterations. The fix was to use the raw `import_from_pypower_ppc()`
path (without the DC susceptance patch) for the AC PF network. This same
issue was documented in the A-2 ACPF result.

## Implications

For any tool evaluation that chains DC and AC analyses (A-4, and potentially
G-FNM-4), the network loading path must be aware of the DC/AC convention
difference. This affects the Accessibility audit (D-4) -- the lack of a
unified loader that works for both DC and AC analysis is a documentation
and usability finding. It also affects cross-tool comparison: other tools
(pandapower, MATPOWER) may handle this convention difference internally.
