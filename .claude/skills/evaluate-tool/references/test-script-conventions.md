# Test Script Conventions

All test scripts follow a consistent format for reproducibility and traceability.

## File Naming

Every test script filename includes both the test ID and a human-readable slug from
the eval-config. The slug is a short snake_case suffix derived from the test description.

```
evaluations/<tool>/tests/<dimension>/test_<id_lower>_<slug>.{py,jl,m}
```

Examples:
- `evaluations/pypsa/tests/expressiveness/test_a1_dcpf.py`
- `evaluations/pypsa/tests/expressiveness/test_a8_stochastic_timeseries.py`
- `evaluations/powermodels/tests/extensibility/test_b3_contingency_loop.jl`
- `evaluations/powermodels/tests/extensibility/test_b9_ptdf_extraction.jl`
- `evaluations/matpower/tests/scalability/test_c1_dcpf.m`

For tier-specific variants, append the tier:
- `test_a1_dcpf_tiny.py` — functional verification on TINY
- `test_a1_dcpf.py` — grade assessment (on the grade network)

## Python Convention

```python
"""
Test <test_id>: <description>

Dimension: <dimension>
Network: <tier> (<network name>)
Pass condition: <from eval-config>
Tool: <tool_name> <version>
"""

import time
import traceback

# Tool-specific imports


def run(network_file: str = "data/networks/<case>.m") -> dict:
    """Execute the test and return structured results.

    Returns:
        dict with keys:
        - status: "pass" | "fail" | "qualified_pass"
        - wall_clock_seconds: float
        - details: dict of test-specific outputs
        - errors: list of error messages (empty if pass)
        - workarounds: list of workaround descriptions (empty if none)
    """
    results = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        # --- Test implementation ---

        # 1. Load network
        # 2. Configure solver (per solver-config.md)
        # 3. Execute the test
        # 4. Extract and validate results
        # 5. Check pass condition

        results["status"] = "pass"
        results["details"] = {
            # Test-specific outputs: dispatch, LMPs, flows, etc.
        }
    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2, default=str))
```

## Julia Convention

```julia
#=
Test <test_id>: <description>

Dimension: <dimension>
Network: <tier> (<network name>)
Pass condition: <from eval-config>
Tool: <tool_name> <version>
=#

using Test

function run(network_file::String = "data/networks/<case>.m")
    results = Dict(
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict(),
        "errors" => String[],
        "workarounds" => String[],
    )

    t0 = time()
    try
        # --- Test implementation ---

        # 1. Load network
        # 2. Configure solver (per solver-config.md)
        # 3. Execute the test
        # 4. Extract and validate results
        # 5. Check pass condition

        results["status"] = "pass"
        results["details"] = Dict(
            # Test-specific outputs
        )
    catch e
        push!(results["errors"], string(typeof(e), ": ", e))
    finally
        results["wall_clock_seconds"] = time() - t0
    end

    return results
end

# Run and print when executed directly
if abspath(PROGRAM_FILE) == @__FILE__
    using JSON
    result = run()
    println(JSON.json(result, 2))
end
```

## Octave Convention

```matlab
%% Test <test_id>: <description>
%%
%% Dimension: <dimension>
%% Network: <tier> (<network name>)
%% Pass condition: <from eval-config>
%% Tool: MATPOWER <version>

function result = run(network_file)
    if nargin < 1
        network_file = 'data/networks/<case>.m';
    end

    result = struct();
    result.status = 'fail';
    result.wall_clock_seconds = 0;
    result.details = struct();
    result.errors = {};
    result.workarounds = {};

    tic;
    try
        %% --- Test implementation ---

        %% 1. Load network
        %% 2. Configure solver
        %% 3. Execute the test
        %% 4. Extract and validate results
        %% 5. Check pass condition

        result.status = 'pass';
        result.details.objective = 0;  % example
    catch e
        result.errors{end+1} = e.message;
    end
    result.wall_clock_seconds = toc;
end

%% Run when executed as script
result = run();
disp(result);
```

## Self-Documentation Requirements

Every test script must include in its header:
1. **Test ID** — exactly as in eval-config (e.g., A-1, B-3, C-5)
2. **Description** — one-line description from eval-config
3. **Dimension** — which criterion this tests
4. **Network** — which tier and network name
5. **Pass condition** — verbatim from eval-config
6. **Tool and version** — tool name and version being tested

## Output Format

The `run()` function returns a dictionary/struct with these standard keys:

| Key | Type | Description |
|-----|------|-------------|
| `status` | string | `"pass"`, `"fail"`, or `"qualified_pass"` |
| `wall_clock_seconds` | float | Execution time |
| `details` | dict | Test-specific outputs (dispatch, LMPs, flows, etc.) |
| `errors` | list | Error messages (empty if pass) |
| `workarounds` | list | Workaround descriptions (empty if none) |

When run as a standalone script (`__main__` / `PROGRAM_FILE`), the output is printed
as JSON to stdout.

## Network File Paths

Use relative paths from the repository root:
- `data/networks/case39.m` (TINY)
- `data/networks/case_ACTIVSg2000.m` (SMALL)
- `data/networks/case_ACTIVSg10k.m` (MEDIUM)

The `run()` function takes the network file as a parameter so the same script can
be pointed at different networks.

## Solver Configuration

Import solver settings from `solver-config.md`. Do not hard-code solver parameters
in test scripts — use named constants or a configuration dict at the top of the file.

## Error Handling

- Catch all exceptions and record them in the `errors` list
- Do NOT let exceptions propagate (the script must always produce output)
- Record tracebacks for debugging
- If a test partially succeeds, still return `"fail"` but include partial results in `details`
