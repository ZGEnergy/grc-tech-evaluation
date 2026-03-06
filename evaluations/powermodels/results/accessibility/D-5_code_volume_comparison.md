---
test_id: D-5
tool: powermodels
dimension: accessibility
status: pass
timestamp: 2026-03-05
---

# D-5: Code Volume Comparison

## Finding

Suite A test scripts for PowerModels range from 72 to 174 lines of code (excluding blanks and comments). Simple PF/OPF tasks (A-1 through A-4) average 93 LOC, while advanced tasks requiring workarounds (A-5, A-7, A-9) average 168 LOC. The code volume reflects the pattern that PowerModels handles basic OPF/PF concisely but requires substantial custom JuMP-level code for SCUC, SCOPF, and contingency analysis.

## Evidence

### Lines of Code per Suite A Test

| Test | Description | Total Lines | Blank | Comment | Code (LOC) | Workaround? |

|------|-------------|-------------|-------|---------|------------|-------------|

| A-1 | DC Power Flow | 91 | 10 | 9 | 72 | No |

| A-2 | AC Power Flow | 123 | 10 | 8 | 105 | No |

| A-3 | DC OPF | 125 | 15 | 10 | 100 | No |

| A-4 | AC Feasibility | 122 | 13 | 14 | 95 | No |

| A-5 | SCUC | 219 | 28 | 27 | 164 | Yes (major) |

| A-6 | SCED | 176 | 21 | 21 | 134 | Yes (major) |

| A-7 | Contingency Sweep | 200 | 17 | 9 | 174 | Yes (custom) |

| A-8 | Stochastic Timeseries | 145 | 16 | 11 | 118 | Yes (moderate) |

| A-9 | SCOPF | 211 | 23 | 23 | 165 | Yes (major) |

| A-10 | Lossy DCOPF LMP | 163 | 19 | 19 | 125 | Yes (moderate) |

| A-11 | Distributed Slack OPF | 180 | 27 | 16 | 137 | Yes (major) |

### Summary Statistics

| Category | Tests | Avg LOC | Min | Max |

|----------|-------|---------|-----|-----|

| Core PF/OPF (no workaround) | A-1, A-2, A-3, A-4 | 93 | 72 | 105 |

| Moderate workaround | A-8, A-10 | 122 | 118 | 125 |

| Major workaround | A-5, A-6, A-7, A-9, A-11 | 155 | 134 | 174 |

| All tests | A-1 to A-11 | 126 | 72 | 174 |

### Code Volume Drivers

**Boilerplate overhead:** Each test includes ~30-40 lines of JSON result scaffolding (Dict construction, error handling, timing). This is test harness overhead, not PowerModels API complexity.

**API calls vs custom code:** For core tests (A-1 through A-4), the actual PowerModels API interaction is 3-5 function calls. The remaining LOC is result extraction from nested `Dict{String,Any}` structures. For workaround tests (A-5, A-9), 60-80 lines are custom JuMP constraint construction that would be unnecessary if PowerModels had built-in SCUC/SCOPF.

**Key inflators:**
- A-7 (174 LOC): Custom BFS graph traversal, combination enumeration, and connectivity checking -- all domain logic that PowerModels does not provide
- A-5 (164 LOC): Binary commitment variables, startup/shutdown logic, min up/down time, ramp constraints built manually via JuMP
- A-9 (165 LOC): Network islanding detection, multi-network contingency setup, objective replacement

### Scripts Location

All scripts at: `evaluations/powermodels/tests/expressiveness/A{1..11}_*.jl`

## Implications

The LOC data confirms the two-tier nature of PowerModels: concise for standard OPF/PF (comparable to other tools), verbose for advanced analysis (due to missing built-in formulations). The 2x LOC increase from core to workaround tests quantifies the developer effort gap. Cross-tool comparison should note that PowerModels LOC includes significant Dict-navigation overhead that typed-struct APIs in other tools would not require.
