%% Test B-5: Export DCPF results to DataFrame and write to CSV
%%
%% Dimension: extensibility
%% Network: TINY (IEEE 39-bus New England)
%% Pass condition: Trivial -- fewer than 5 lines of code beyond the solve.
%%   No custom serialization logic required.
%% Tool: MATPOWER 8.1

function result = test_b5_interoperability(network_file)
    if nargin < 1
        network_file = '/workspace/data/networks/case39.m';
    end
