---
test_id: E-1
tool: powermodels
dimension: maturity
status: qualified_pass
timestamp: 2026-03-05
---

# E-1: Release Cadence

## Finding

PowerModels.jl has maintained a healthy release cadence with 8 releases in the last 24 months (Mar 2024 - Mar 2026), averaging one release every ~3 months. However, the project remains at v0.x after 8+ years, indicating the API is not yet considered stable.

## Evidence

Releases in the last 24 months (from GitHub Releases page):

| Version | Date |

|---------|------|

| v0.21.5 | 2025-08-12 |

| v0.21.4 | 2025-05-20 |

| v0.21.3 | 2024-11-04 |

| v0.21.2 | 2024-07-05 |

| v0.21.1 | 2024-03-16 |

| v0.21.0 | 2024-01-19 |

| v0.20.1 | 2024-01-10 |

| v0.20.0 | 2024-01-02 |

All releases follow semver (v0.MAJOR.MINOR). The project has 30+ total releases since 2016.

Most recent release: v0.21.5 (2025-08-12) -- approximately 7 months ago.
Most recent push to master: 2025-12-01.

Source: <https://github.com/lanl-ansi/PowerModels.jl/releases>

## Implications

The release cadence is adequate for a research-oriented tool -- 8 releases in 24 months is more frequent than many academic packages. The perpetual v0.x status is a concern for production adoption as it signals the maintainers reserve the right to make breaking API changes. In Julia ecosystem convention, v0.x packages are common even for mature tools, so this is less alarming than it would be in Python/npm ecosystems but still notable.
