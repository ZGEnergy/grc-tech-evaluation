%% Test B-1: Add flow gate limit to DC OPF and extract dual values
%%
%% Dimension: extensibility
%% Network: TINY (IEEE 39-bus New England)
%% Pass condition: Achievable through documented API. No source patching.
%%   Dual value of custom constraint extractable and correctly reflects binding status.
%%   Include BOTH non-binding (dual=0) AND binding case.
%% Tool: MATPOWER 8.1
%% Solver: GLPK

function result = test_b1_custom_constraints(network_file, timeseries_dir)
    if nargin < 1
        network_file = '/workspace/data/networks/case39.m';
    end
