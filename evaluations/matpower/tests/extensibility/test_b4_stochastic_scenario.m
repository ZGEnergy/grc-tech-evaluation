%% Test B-4: Generate 20 scenarios, solve 12hr multi-period DCOPF for each, collect results
%%
%% Dimension: extensibility
%% Network: TINY (IEEE 39-bus New England)
%% Pass condition: Tool accepts timeseries inputs programmatically. Scenario loop
%%   expressible without excessive overhead. Results collectable.
%% Tool: MATPOWER 8.1
%% Solver: GLPK (fallback from HiGHS -- HiGHS unavailable in Octave devcontainer)

function result = test_b4_stochastic_scenario(network_file, timeseries_dir)
    if nargin < 1
        network_file = '/workspace/data/networks/case39.m';
    end
