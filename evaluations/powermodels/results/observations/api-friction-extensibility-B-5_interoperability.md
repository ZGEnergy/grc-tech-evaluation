---
tag: api-friction
dimension: extensibility
test_id: B-5
tool: powermodels
---

# API Friction: Dict-Based Results Require Manual Tabular Export

PowerModels returns all results as nested `Dict{String,Any}` with string keys. There is no built-in conversion to DataFrames or tabular formats. Additionally, DataFrames.jl and CSV.jl are not included as dependencies.

Export to CSV is achievable in 4 lines of manual I/O (meeting the "fewer than 5 lines" criterion), but the Dict-based structure means users must manually iterate over results and handle type conversions. Tools with native DataFrame output (e.g., pandapower) provide a more ergonomic data export experience.

The evaluation Project.toml does not include DataFrames.jl or CSV.jl, so the test used manual Julia I/O as a fallback. Adding these standard packages would reduce export to 2 lines.
