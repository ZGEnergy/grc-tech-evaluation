---
tag: workaround-needed
source_dimension: expressiveness
source_test: A-9
tool: powersimulations
severity: medium
timestamp: "2026-03-24T00:00:00Z"
---

# Observation: No Built-in SCOPF in PowerSimulations.jl

## Finding

PowerSimulations.jl lacks built-in SCOPF capability. N-1 security-constrained OPF must be
manually assembled using LODF matrices from PowerNetworkMatrices.jl and JuMP model access,
requiring approximately 50 lines of domain-specific constraint code.

## Context

During A-9 (SCOPF test), N-1 contingency constraints were added by computing the full LODF
matrix via `LODF(sys)`, accessing PSI's internal flow variables via `PSI.get_variables()`,
and injecting constraints via JuMP's `@constraint` macro. The approach requires knowledge of:
(1) LODF-based post-contingency flow estimation, (2) islanding detection (branches where
|LODF| >= 1.0), and (3) correct constraint directionality. Legacy N-1/G-1 code existed but
was removed in v0.33.0 and was undocumented in v0.30.2.

## Implications

The workaround uses documented public APIs from three ecosystem packages (PowerNetworkMatrices,
PowerSimulations, JuMP), classifying it as a stable workaround. This should be noted in the
Extensibility assessment (B-1 custom constraint API) as evidence that JuMP model access enables
arbitrary constraint injection, but that SCOPF-specific convenience is missing from the
framework. The effort level (~50 lines) is moderate and requires domain expertise.
