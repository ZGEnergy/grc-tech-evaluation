%% Test B-2: Network Graph Access — BFS to depth 3 on IEEE 39-bus (TINY)
%%
%% Pass condition: From a chosen bus, run BFS to depth 3. Return all buses
%% and branches within that subgraph.
%%
%% MATPOWER has no graph object; we build adjacency from mpc.branch(:, [F_BUS T_BUS]).
%%
%% Usage (from evaluations/matpower/):
%%   octave tests/extensibility/test_b2_graph_access_tiny.m

% Add MATPOWER to path
mp_root = fullfile(pwd, "matpower8.1");
addpath(fullfile(mp_root, "lib"));
addpath(fullfile(mp_root, "data"));
addpath(fullfile(mp_root, "mips", "lib"));
addpath(fullfile(mp_root, "mp-opt-model", "lib"));
addpath(fullfile(mp_root, "mptest", "lib"));

network_file = fullfile(pwd, "..", "..", "data", "networks", "case39.m");

fprintf("\n========================================\n");
fprintf("TEST B-2: Graph Access (BFS depth 3) on TINY (IEEE 39-bus)\n");
fprintf("========================================\n");

status = "fail";
wall_clock = 0;
loc = 0;

tic_val = tic();
try
    % --- Load case ---
    mpc = loadcase(network_file);
    define_constants;

    % --- Build adjacency list from branch data ---
    n_bus = size(mpc.bus, 1);
    bus_ids = mpc.bus(:, BUS_I);
    n_branch = size(mpc.branch, 1);
    from_bus = mpc.branch(:, F_BUS);
    to_bus = mpc.branch(:, T_BUS);

    % Create a map from bus ID to index (1..n_bus)
    max_bus_id = max(bus_ids);
    bus_id_to_idx = zeros(max_bus_id, 1);
    for i = 1:n_bus
        bus_id_to_idx(bus_ids(i)) = i;
    end

    % Build adjacency list as cell array
    adj = cell(n_bus, 1);
    adj_branch = cell(n_bus, 1);  % track which branch index connects
    for i = 1:n_bus
        adj{i} = [];
        adj_branch{i} = [];
    end
    for k = 1:n_branch
        fi = bus_id_to_idx(from_bus(k));
        ti = bus_id_to_idx(to_bus(k));
        adj{fi} = [adj{fi}, ti];
        adj{ti} = [adj{ti}, fi];
        adj_branch{fi} = [adj_branch{fi}, k];
        adj_branch{ti} = [adj_branch{ti}, k];
    end

    fprintf("Adjacency list built: %d buses, %d branches\n", n_bus, n_branch);

    % --- BFS from bus 16 (chosen as mid-network bus) to depth 3 ---
    start_bus_id = 16;
    max_depth = 3;
    start_idx = bus_id_to_idx(start_bus_id);

    visited = false(n_bus, 1);
    depth_map = -ones(n_bus, 1);
    queue = [start_idx];
    visited(start_idx) = true;
    depth_map(start_idx) = 0;

    subgraph_buses = [start_idx];
    subgraph_branches = [];

    head = 1;
    while head <= length(queue)
        curr = queue(head);
        head = head + 1;
        curr_depth = depth_map(curr);

        if curr_depth >= max_depth
            continue
        end

        neighbors = adj{curr};
        br_indices = adj_branch{curr};
        for j = 1:length(neighbors)
            nb = neighbors(j);
            br = br_indices(j);
            if ~visited(nb)
                visited(nb) = true;
                depth_map(nb) = curr_depth + 1;
                queue = [queue, nb];
                subgraph_buses = [subgraph_buses, nb];
            end
            % Include branch if both endpoints are visited
            if visited(nb) && ~ismember(br, subgraph_branches)
                subgraph_branches = [subgraph_branches, br];
            end
        end
    end

    % Convert indices back to bus IDs
    subgraph_bus_ids = sort(bus_ids(subgraph_buses));
    subgraph_branches = sort(unique(subgraph_branches));

    wall_clock = toc(tic_val);

    fprintf("\nBFS from bus %d, depth %d:\n", start_bus_id, max_depth);
    fprintf("  Buses found: %d\n", length(subgraph_bus_ids));
    fprintf("  Branches found: %d\n", length(subgraph_branches));

    fprintf("\n  Bus IDs: ");
    fprintf("%d ", subgraph_bus_ids);
    fprintf("\n");

    fprintf("  Branch indices: ");
    fprintf("%d ", subgraph_branches);
    fprintf("\n");

    % Print depth breakdown
    for d = 0:max_depth
        buses_at_d = bus_ids(depth_map == d);
        fprintf("  Depth %d: %d buses [", d, length(buses_at_d));
        fprintf("%d ", sort(buses_at_d));
        fprintf("]\n");
    end

    % --- Validate ---
    assert(length(subgraph_bus_ids) > 1, "BFS found only the start bus");
    assert(length(subgraph_branches) > 0, "BFS found no branches");
    assert(ismember(start_bus_id, subgraph_bus_ids), "Start bus not in subgraph");

    % Verify all branches connect buses within the subgraph
    all_branches_valid = true;
    for k = 1:length(subgraph_branches)
        br = subgraph_branches(k);
        f = from_bus(br);
        t = to_bus(br);
        if ~ismember(f, subgraph_bus_ids) || ~ismember(t, subgraph_bus_ids)
            fprintf("  WARN: Branch %d (%d->%d) has endpoint outside subgraph\n", br, f, t);
            all_branches_valid = false;
        end
    end
    assert(all_branches_valid, "Some branches have endpoints outside subgraph");

    fprintf("\nAll subgraph branches connect buses within the subgraph: YES\n");

    status = "pass";
    loc = 60;  % approximate core BFS logic lines

catch err
    wall_clock = toc(tic_val);
    fprintf("ERROR: %s\n", err.message);
    status = "fail";
end

fprintf("\n========================================\n");
fprintf("STATUS: %s\n", status);
fprintf("WALL_CLOCK: %.4f\n", wall_clock);
fprintf("LOC: %d\n", loc);
fprintf("========================================\n");
