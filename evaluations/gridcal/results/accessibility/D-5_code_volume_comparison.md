---
test_id: D-5
tool: gridcal
dimension: accessibility
network: N/A
protocol_version: "v4"
status: informational
workaround_class: null
timestamp: 2026-03-06T04:00:00Z
---

# D-5: Code Volume Comparison

## Result: INFORMATIONAL

## Methodology

Lines of code (LOC) counted from the test scripts in `evaluations/gridcal/tests/expressiveness/`. LOC includes imports, setup, solve, and result extraction -- excludes blank lines and comments. Values taken from the YAML front matter of each test result file.

## GridCal LOC per Suite A Test

| Test | Description | Status | LOC |
|------|-------------|--------|-----|
| A-1 | DCPF | pass | 30 |
| A-2 | ACPF | pass | 45 |
| A-3 | DC OPF | pass | 45 |
| A-4 | AC Feasibility | pass | 55 |
| A-5 | SCUC | fail | 85 |
| A-6 | SCED | fail | 180 |
| A-7 | N-M Contingency | qualified_pass | 85 |
| A-8 | Stochastic TS OPF | fail | 80 |
| A-9 | SCOPF | fail | 60 |
| A-10 | Lossy DCOPF | qualified_pass | 50 |
| A-11 | Distributed Slack | fail | 55 |

## Analysis

**Passing tests (A-1 through A-4):** LOC ranges from 30 to 55. These are reasonable code volumes for the tasks involved. The convenience API (`vge.power_flow()`, `vge.linear_opf()`, `vge.open_file()`) keeps the common cases concise.

**Failed tests (A-5, A-6, A-8, A-9, A-11):** LOC is inflated because the test scripts include multiple attempted approaches, error handling for known crashes, and documentation of failure modes. A-6 (SCED) at 180 LOC reflects three separate approaches tried (snapshot OPF, ramp test, time-series OPF), all of which failed the protocol requirements.

**Qualified passes (A-7, A-10):** Moderate LOC (50-85). A-7's 85 lines includes manual N-M contingency loop with NetworkX graph traversal -- a workaround for the missing built-in N-M capability.

## Key Observations

1. **Simple analyses are concise.** DCPF in 30 LOC and DC OPF in 45 LOC indicate a clean API for core use cases.

2. **LOC increases sharply for advanced analyses** that require workarounds or multiple approaches. This reflects the tool's narrower feature scope beyond basic PF/OPF.

3. **Failed tests still produce LOC** because the evaluator attempted the analysis and documented the failure mode. This LOC should not be compared against passing tests in other tools.

4. **No DataFrame accessor on OPF results.** Power flow results have `get_bus_df()` / `get_branch_df()`, but OPF results require manual numpy array handling, adding a few lines of boilerplate for result extraction.

## Cross-Tool Comparison Note

This table records GridCal's LOC only. Cross-tool comparison requires the same test LOC data from other evaluated tools.
