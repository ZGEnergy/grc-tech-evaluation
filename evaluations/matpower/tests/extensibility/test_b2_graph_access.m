%% Test B-2: BFS to depth 3 from a chosen bus, return subgraph
%%
%% Dimension: extensibility
%% Network: TINY (IEEE 39-bus New England)
%% Pass condition: Works via native graph primitives or clean export.
%% Tool: MATPOWER 8.1

function result = test_b2_graph_access(network_file)
    if nargin < 1
        network_file = '/workspace/data/networks/case39.m';
    end
