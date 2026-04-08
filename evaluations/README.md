# Evaluations

Each subdirectory is an independent evaluation environment for one tool.
All six evaluations are complete (protocol v11).

## Per-Tool Structure

```
evaluations/<tool>/
├── results/
│   ├── synthesis.md            # Comprehensive assessment (~3000 words)
│   ├── eval-config.yaml        # Test configuration and parameters
│   ├── validation-report.md    # Automated validation checks
│   ├── .progress.yaml          # Evaluation state machine status
│   ├── gate/                   # G-1 to G-3: network ingestion tests
│   ├── expressiveness/         # A-1 to A-12: problem formulation tests
│   ├── extensibility/          # B-1 to B-9: custom constraint/callback tests
│   ├── scalability/            # C-1 to C-10: scaling tests (39 to 10k buses)
│   ├── accessibility/          # D-1 to D-5: documentation and installation
│   ├── maturity/               # E-1 to E-6: code quality, CI, bus factor
│   ├── supply_chain/           # License and open-source gate criteria
│   ├── observations/           # Tool-specific research findings
│   └── p2_readiness/           # Phase 2 gap analysis
├── tests/                      # Test scripts organized by dimension
├── pyproject.toml / Project.toml  # Language-specific dependency file
└── verify_install.py / .jl / .m   # Smoke test
```

## Reading Results

Start with `results/synthesis.md` for each tool — it summarizes strengths,
weaknesses, workarounds, and the overall assessment. Individual test results
in dimension subdirectories contain detailed pass/fail outcomes with evidence.

## Shared Resources

The `shared/` subdirectory contains cross-tool utilities:

- `matpower_loader.py` — Shared MATPOWER case file parser used by Python tools
