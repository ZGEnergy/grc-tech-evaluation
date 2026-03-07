---
test_id: D-5
tool: powermodels
dimension: accessibility
network: N/A
protocol_version: "v4"
status: informational
workaround_class: null
timestamp: 2026-03-07T00:00:00Z
---

# D-5: Lines of code for each Suite A test script

## Result: INFORMATIONAL

## Finding

Suite A test scripts range from 124 LOC (A-3, DCOPF) to 406 LOC (A-6, SCED). There is a clear bimodal distribution: tests using PowerModels built-in functions average ~131 LOC, while tests requiring user-assembled JuMP formulations average ~355 LOC. The code volume directly correlates with whether PowerModels provides a built-in problem type.

## Evidence

### LOC by Test

| Test | Description | Total LOC | Code LOC | Built-in? |
|------|-------------|-----------|----------|-----------|
| A-1  | DCPF | 131 | 99 | Yes (`compute_dc_pf` / `solve_dc_pf`) |
| A-2  | ACPF | 144 | 112 | Yes (`solve_ac_pf`) |
| A-3  | DCOPF | 124 | 95 | Yes (`solve_dc_opf`) |
| A-4  | AC feasibility | 226 | 173 | Partial (uses `solve_ac_pf` + custom logic) |
| A-5  | SCUC | 295 | 220 | No (user-assembled JuMP) |
| A-6  | SCED | 406 | 333 | No (user-assembled JuMP, two-stage) |
| A-7  | Contingency sweep | 333 | 250 | No (manual loop + deepcopy) |
| A-8  | Stochastic time-series | 132 | 103 | Partial (multi-network framework) |
| A-9  | SCOPF | 331 | 260 | No (user-assembled JuMP) |
| A-10 | Lossy DCOPF/LMP | 367 | 268 | No (user-assembled, dual extraction) |
| A-11 | Distributed slack OPF | 396 | 280 | No (user-assembled PTDF) |
| | **Total** | **2,885** | **2,193** | |
| | **Mean** | **262** | **199** | |
| | **Median** | **295** | **220** | |

Notes:
- "Total LOC" = all lines including blanks and comments (`wc -l`)
- "Code LOC" = non-blank, non-comment lines (`grep -v '^\s*$' | grep -v '^\s*#'`)
- Each script includes ~30 lines of boilerplate (results dict setup, JSON output, try/catch wrapper)

### Distribution Analysis

**Built-in problem types (A-1, A-2, A-3, A-8):**
- Mean: 133 LOC total, 102 code LOC
- These tests primarily call a single `solve_*` function and extract results

**Partially built-in (A-4):**
- 226 LOC total, 173 code LOC
- Uses built-in solver but adds custom feasibility logic

**User-assembled (A-5, A-6, A-7, A-9, A-10, A-11):**
- Mean: 355 LOC total, 269 code LOC
- These tests build JuMP models from scratch, using PowerModels only for data parsing
- A-6 (SCED) is the largest at 406/333 LOC due to two-stage decomposition

### Code Volume Ratio

User-assembled tests require approximately **2.7x more code** than built-in tests (269 vs 102 code LOC). This ratio understates the difficulty gap because user-assembled tests also require:
- Deep JuMP/MathOptInterface knowledge
- Understanding of PowerModels internal data structures
- Manual constraint formulation for power system equations
- Custom result extraction logic

## Implications

The LOC distribution reveals that PowerModels is highly accessible for its core use case (PF/OPF in ~100 lines) but requires substantial user effort for anything beyond built-in problems. 6 of 11 Suite A tests (55%) required user-assembled JuMP formulations averaging 269 code lines, indicating that the tool's accessibility drops sharply outside its built-in problem portfolio. The total evaluation code volume of 2,885 lines is moderate but heavily weighted toward the user-assembled problems.
