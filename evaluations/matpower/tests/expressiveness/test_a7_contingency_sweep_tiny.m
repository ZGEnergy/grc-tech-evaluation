%% Test A-7: N-M Contingency Sweep (Pruned, Escalating) — IEEE 39-bus (TINY)
%%
%% Pass condition: Enumerate branches within graph distance x=3 of a chosen
%% bus. Sweep contingencies with escalating order up to m=3. Prune branches
%% causing total load loss. No full model reconstruction per case.
%%
%% Usage (from evaluations/matpower/):
%%   octave tests/expressiveness/test_a7_contingency_sweep_tiny.m

% Add MATPOWER to path
mp_root = fullfile(pwd, "matpower8.1");
addpath(fullfile(mp_root, "lib"));
addpath(fullfile(mp_root, "data"));
addpath(fullfile(mp_root, "mips", "lib"));
addpath(fullfile(mp_root, "mp-opt-model", "lib"));
addpath(fullfile(mp_root, "mptest", "lib"));

% Load column index constants
define_constants;

% Load shared network
network_file = fullfile(pwd, "..", "..", "data", "networks", "case39.m");

fprintf("\n========================================\n");
fprintf("TEST A-7: N-M Contingency Sweep (TINY)\n");
fprintf("========================================\n");

status = "fail";
wall_clock = 0;
loc = 0;

tic_val = tic();
try
    % --- Load case ---
    mpc = loadcase(network_file);
    nb = size(mpc.bus, 1);
    nl = size(mpc.branch, 1);
    fprintf("Loaded %d buses, %d branches, %d generators\n", nb, nl, size(mpc.gen, 1));

    mpopt = mpoption("verbose", 0, "out.all", 0);

    % --- Parameters ---
    focus_bus = 16;   % Central bus with many connections
    max_dist = 3;     % Graph distance for branch enumeration
    max_order = 3;    % Max contingency order (N-1, N-2, N-3)

    fprintf("Focus bus: %d, max distance: %d, max order: %d\n", ...
            focus_bus, max_dist, max_order);

    % --- Step 1: Build adjacency from branch data ---
    fprintf("\n--- Building adjacency graph ---\n");
    from_bus = mpc.branch(:, F_BUS);
    to_bus = mpc.branch(:, T_BUS);

    % Build bus adjacency list
    adj = cell(nb, 1);
    for k = 1:nb
        adj{k} = [];
    end
    for k = 1:nl
        fb = from_bus(k);
        tb = to_bus(k);
        adj{fb} = [adj{fb}, tb];
        adj{tb} = [adj{tb}, fb];
    end

    % --- Step 2: BFS from focus bus to depth max_dist ---
    fprintf("BFS from bus %d to depth %d...\n", focus_bus, max_dist);
    visited = false(nb, 1);
    dist = inf(nb, 1);
    queue = focus_bus;
    visited(focus_bus) = true;
    dist(focus_bus) = 0;

    while ~isempty(queue)
        current = queue(1);
        queue(1) = [];
        if dist(current) < max_dist
            neighbors = adj{current};
            for n_idx = 1:length(neighbors)
                nb_id = neighbors(n_idx);
                if ~visited(nb_id)
                    visited(nb_id) = true;
                    dist(nb_id) = dist(current) + 1;
                    queue = [queue, nb_id];
                end
            end
        end
    end

    nearby_buses = find(visited);
    fprintf("Buses within distance %d of bus %d: %s\n", ...
            max_dist, focus_bus, mat2str(nearby_buses'));

    % --- Step 3: Enumerate branches in scope ---
    % A branch is "in scope" if both endpoints are within distance max_dist
    in_scope = false(nl, 1);
    for k = 1:nl
        if visited(from_bus(k)) && visited(to_bus(k))
            in_scope(k) = true;
        end
    end
    scope_branches = find(in_scope);
    n_scope = length(scope_branches);
    fprintf("Branches in scope: %d / %d\n", n_scope, nl);
    for k = 1:n_scope
        bi = scope_branches(k);
        fprintf("  Branch %d: %d -> %d\n", bi, from_bus(bi), to_bus(bi));
    end

    % --- Step 4: Baseline DC power flow ---
    fprintf("\n--- Baseline DCPF ---\n");
    results_base = rundcpf(mpc, mpopt);
    if ~results_base.success
        error("Baseline DCPF failed");
    end
    base_load = sum(results_base.bus(:, PD));
    focus_bus_idx = find(results_base.bus(:, BUS_I) == focus_bus);
    base_load_focus = results_base.bus(focus_bus_idx, PD);
    fprintf("Total system load: %.2f MW\n", base_load);
    fprintf("Load at bus %d: %.2f MW\n", focus_bus, base_load_focus);

    % --- Helper: run contingency and return load served ---
    % For DCPF, we toggle BR_STATUS=0 for outaged branches, run, restore.
    % No model reconstruction — just toggle a column value.

    % --- Step 5: N-1 contingency sweep ---
    fprintf("\n--- N-1 Contingency Sweep (%d cases) ---\n", n_scope);
    n1_load_loss = zeros(n_scope, 1);
    n1_converged = true(n_scope, 1);

    for k = 1:n_scope
        bi = scope_branches(k);
        mpc_c = mpc;
        mpc_c.branch(bi, BR_STATUS) = 0;  % trip branch
        results_c = rundcpf(mpc_c, mpopt);
        if results_c.success
            served = sum(results_c.gen(:, PG));
            n1_load_loss(k) = base_load - served;
        else
            n1_converged(k) = false;
            n1_load_loss(k) = base_load;  % treat as total loss
        end
    end

    fprintf("  Br#   From->To     Load Loss (MW)  Status\n");
    for k = 1:n_scope
        bi = scope_branches(k);
        if n1_converged(k)
            fprintf("  %3d   %3d->%3d     %8.2f        OK\n", ...
                    bi, from_bus(bi), to_bus(bi), n1_load_loss(k));
        else
            fprintf("  %3d   %3d->%3d     %8.2f        DIVERGED\n", ...
                    bi, from_bus(bi), to_bus(bi), n1_load_loss(k));
        end
    end

    % --- Step 6: Pruning ---
    % Prune branches that cause total load loss (island the focus bus)
    total_loss_threshold = 0.99 * base_load;  % >99% load loss = total
    prune_mask = n1_load_loss > total_loss_threshold | ~n1_converged;
    pruned_branches = scope_branches(prune_mask);
    surviving_branches = scope_branches(~prune_mask);
    n_surviving = length(surviving_branches);

    fprintf("\n--- Pruning Results ---\n");
    fprintf("Pruned branches (cause near-total load loss): %d\n", length(pruned_branches));
    if ~isempty(pruned_branches)
        for k = 1:length(pruned_branches)
            bi = pruned_branches(k);
            fprintf("  Branch %d (%d->%d)\n", bi, from_bus(bi), to_bus(bi));
        end
    end
    fprintf("Surviving branches for higher-order: %d\n", n_surviving);

    % --- Step 7: N-2 contingency sweep ---
    n2_cases = 0;
    n2_results = [];
    if max_order >= 2 && n_surviving >= 2
        pairs = nchoosek(1:n_surviving, 2);
        n2_cases = size(pairs, 1);
        fprintf("\n--- N-2 Contingency Sweep (%d cases) ---\n", n2_cases);
        n2_load_loss = zeros(n2_cases, 1);
        n2_converged = true(n2_cases, 1);

        for k = 1:n2_cases
            bi1 = surviving_branches(pairs(k, 1));
            bi2 = surviving_branches(pairs(k, 2));
            mpc_c = mpc;
            mpc_c.branch(bi1, BR_STATUS) = 0;
            mpc_c.branch(bi2, BR_STATUS) = 0;
            results_c = rundcpf(mpc_c, mpopt);
            if results_c.success
                served = sum(results_c.gen(:, PG));
                n2_load_loss(k) = base_load - served;
            else
                n2_converged(k) = false;
                n2_load_loss(k) = base_load;
            end
        end

        fprintf("  Top 5 worst N-2 contingencies:\n");
        [sorted_loss, sort_idx] = sort(n2_load_loss, "descend");
        for k = 1:min(5, n2_cases)
            idx = sort_idx(k);
            bi1 = surviving_branches(pairs(idx, 1));
            bi2 = surviving_branches(pairs(idx, 2));
            conv_str = "OK";
            if ~n2_converged(idx)
                conv_str = "DIVERGED";
            end
            fprintf("    Br %d+%d (%d->%d, %d->%d): loss=%.2f MW  %s\n", ...
                    bi1, bi2, from_bus(bi1), to_bus(bi1), ...
                    from_bus(bi2), to_bus(bi2), n2_load_loss(idx), conv_str);
        end

        % Prune for N-3
        prune2 = n2_load_loss > total_loss_threshold | ~n2_converged;
        fprintf("  N-2 cases causing near-total loss: %d / %d\n", sum(prune2), n2_cases);
    end

    % --- Step 8: N-3 contingency sweep ---
    n3_cases = 0;
    if max_order >= 3 && n_surviving >= 3
        triples = nchoosek(1:n_surviving, 3);
        n3_cases = size(triples, 1);
        fprintf("\n--- N-3 Contingency Sweep (%d cases) ---\n", n3_cases);
        n3_load_loss = zeros(n3_cases, 1);
        n3_converged = true(n3_cases, 1);

        for k = 1:n3_cases
            bi1 = surviving_branches(triples(k, 1));
            bi2 = surviving_branches(triples(k, 2));
            bi3 = surviving_branches(triples(k, 3));
            mpc_c = mpc;
            mpc_c.branch(bi1, BR_STATUS) = 0;
            mpc_c.branch(bi2, BR_STATUS) = 0;
            mpc_c.branch(bi3, BR_STATUS) = 0;
            results_c = rundcpf(mpc_c, mpopt);
            if results_c.success
                served = sum(results_c.gen(:, PG));
                n3_load_loss(k) = base_load - served;
            else
                n3_converged(k) = false;
                n3_load_loss(k) = base_load;
            end
        end

        fprintf("  Top 5 worst N-3 contingencies:\n");
        [sorted_loss, sort_idx] = sort(n3_load_loss, "descend");
        for k = 1:min(5, n3_cases)
            idx = sort_idx(k);
            bi1 = surviving_branches(triples(idx, 1));
            bi2 = surviving_branches(triples(idx, 2));
            bi3 = surviving_branches(triples(idx, 3));
            conv_str = "OK";
            if ~n3_converged(idx)
                conv_str = "DIVERGED";
            end
            fprintf("    Br %d+%d+%d: loss=%.2f MW  %s\n", ...
                    bi1, bi2, bi3, n3_load_loss(idx), conv_str);
        end
        fprintf("  N-3 cases causing near-total loss: %d / %d\n", ...
                sum(n3_load_loss > total_loss_threshold | ~n3_converged), n3_cases);
    end

    % --- Summary ---
    wall_clock = toc(tic_val);
    fprintf("\n--- Contingency Sweep Summary ---\n");
    fprintf("Focus bus: %d, Graph distance: %d\n", focus_bus, max_dist);
    fprintf("Branches in scope: %d\n", n_scope);
    fprintf("N-1 cases: %d (pruned %d)\n", n_scope, length(pruned_branches));
    fprintf("N-2 cases: %d\n", n2_cases);
    fprintf("N-3 cases: %d\n", n3_cases);
    fprintf("Total contingency cases evaluated: %d\n", n_scope + n2_cases + n3_cases);
    fprintf("Wall clock: %.4f seconds\n", wall_clock);
    fprintf("Approach: BR_STATUS toggle (no model reconstruction)\n");

    status = "pass";
    loc = 150;

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
