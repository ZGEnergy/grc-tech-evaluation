%% Test B-8: Solve DC OPF with three slack configurations and compare LMPs
%%
%% Dimension: extensibility
%% Network: TINY (IEEE 39-bus New England)
%% Pass condition: Reference bus configurable via API without model reconstruction.
%%   LMP values change consistently across configurations.
%% Tool: MATPOWER 8.1
%% Solver: GLPK (fallback from HiGHS)

function result = test_b8_reference_bus_config(network_file, timeseries_dir)
    if nargin < 1
        network_file = '/workspace/data/networks/case39.m';
    end
