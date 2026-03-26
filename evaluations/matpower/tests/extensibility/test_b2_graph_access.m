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

    result = struct();
    result.status = 'fail';
    result.wall_clock_seconds = 0;
    result.details = struct();
    result.errors = {};
    result.workarounds = {};

    %% Setup MATPOWER
    mp_root = fullfile(fileparts(mfilename('fullpath')), '..', '..', 'matpower8.1');
    addpath(fullfile(mp_root, 'lib'));
    addpath(fullfile(mp_root, 'data'));
    addpath(fullfile(mp_root, 'mips', 'lib'));
    addpath(fullfile(mp_root, 'mp-opt-model', 'lib'));
    addpath(fullfile(mp_root, 'mptest', 'lib'));

    tic;
    try
        %% Load case
        mpc = loadcase(network_file);
        define_constants;

        nb = size(mpc.bus, 1);
        nl = size(mpc.branch, 1);
        bus_nums = mpc.bus(:, BUS_I);

        %% Build adjacency matrix from branch data
        f_bus = mpc.branch(:, F_BUS);
        t_bus = mpc.branch(:, T_BUS);

        %% Map bus numbers to indices (case39 has 1-indexed buses but not all cases do)
        bus_map = containers.Map('KeyType', 'int32', 'ValueType', 'int32');
        for i = 1:nb
            bus_map(int32(bus_nums(i))) = int32(i);
        end

        %% Build sparse adjacency matrix
        f_idx = zeros(nl, 1);
        t_idx = zeros(nl, 1);
        for i = 1:nl
            f_idx(i) = bus_map(int32(f_bus(i)));
            t_idx(i) = bus_map(int32(t_bus(i)));
        end
        adj = sparse(f_idx, t_idx, ones(nl, 1), nb, nb);
        adj = adj + adj';  % undirected
        adj = adj > 0;     % binary

        %% Choose start bus: bus 16 (central in case39)
        start_bus = 16;
        start_idx = bus_map(int32(start_bus));
        max_depth = 3;

        fprintf('=== BFS from bus %d, depth %d ===\n', start_bus, max_depth);

        %% BFS implementation
        visited = false(nb, 1);
        visited(start_idx) = true;
        depth_of = -ones(nb, 1);
        depth_of(start_idx) = 0;
        queue = start_idx;
        q_depth = 0;

        buses_by_depth = cell(max_depth + 1, 1);
        buses_by_depth{1} = start_bus;

        while ~isempty(queue)
            cur = queue(1);
            queue(1) = [];
            cd = q_depth(1);
            q_depth(1) = [];

            if cd >= max_depth
                continue;
            end

            neighbors = find(adj(cur, :));
            for nn = neighbors
                if ~visited(nn)
                    visited(nn) = true;
                    depth_of(nn) = cd + 1;
                    queue(end + 1) = nn;
                    q_depth(end + 1) = cd + 1;
                    buses_by_depth{cd + 2}(end + 1) = bus_nums(nn);
                end
            end
        end

        %% Collect subgraph buses and branches
        subgraph_bus_idx = find(visited);
        subgraph_bus_nums = bus_nums(subgraph_bus_idx);
        n_sub_buses = length(subgraph_bus_idx);

        %% Subgraph branches: both endpoints in visited set
        subgraph_branches = [];
        for i = 1:nl
            if visited(f_idx(i)) && visited(t_idx(i))
                subgraph_branches(end + 1) = i;
            end
        end
        n_sub_branches = length(subgraph_branches);

        fprintf('Subgraph buses: %d / %d (%.0f%%)\n', n_sub_buses, nb, 100*n_sub_buses/nb);
        fprintf('Subgraph branches: %d / %d (%.0f%%)\n', n_sub_branches, nl, 100*n_sub_branches/nl);

        %% Print buses by depth
        for d = 0:max_depth
            buses_at_d = buses_by_depth{d + 1};
            if ~isempty(buses_at_d)
                fprintf('Depth %d: %s\n', d, mat2str(sort(buses_at_d)));
            end
        end

        %% Also test MATPOWER's native find_islands()
        groups = find_islands(mpc);
        n_islands = length(groups);
        fprintf('Network islands (find_islands): %d\n', n_islands);

        %% Peak memory
        [~, mem_out] = system('grep VmHWM /proc/self/status');
        peak_kb = sscanf(mem_out, 'VmHWM: %f');
        if ~isempty(peak_kb)
            peak_memory_mb = peak_kb / 1024;
        else
            peak_memory_mb = -1;
        end

        %% Store results
        result.details.start_bus = start_bus;
        result.details.max_depth = max_depth;
        result.details.n_subgraph_buses = n_sub_buses;
        result.details.n_subgraph_branches = n_sub_branches;
        result.details.total_buses = nb;
        result.details.total_branches = nl;
        result.details.n_islands = n_islands;
        result.details.peak_memory_mb = peak_memory_mb;

        %% Pass condition: BFS works and returns reasonable subgraph
        if n_sub_buses > 1 && n_sub_branches > 0
            result.status = 'pass';
            fprintf('\n=== PASS: BFS subgraph extraction successful ===\n');
        else
            result.errors{end+1} = 'BFS returned empty or trivial subgraph';
        end

    catch e
        result.errors{end+1} = e.message;
        fprintf('ERROR: %s\n', e.message);
    end
    result.wall_clock_seconds = toc;
end

%% Run when executed as script
result = test_b2_graph_access();
disp(result);
disp(result.details);
