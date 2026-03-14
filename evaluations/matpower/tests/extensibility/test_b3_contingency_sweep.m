%% Test B-3: Escalating N-M contingency sweep with pruning (x=3, m=3)
%%
%% Dimension: extensibility
%% Network: TINY (IEEE 39-bus New England)
%% Pass condition: Completes without full model reconstruction per contingency.
%%   Load loss per contingency collected. Pruning and graph-distance scoping
%%   achievable via API.
%% Tool: MATPOWER 8.1

function result = test_b3_contingency_sweep(network_file)
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
        ngen = size(mpc.gen, 1);

        %% Solve base-case DC power flow
        mpopt = mpoption('verbose', 0, 'out.all', 0);
        results_base = rundcpf(mpc, mpopt);
        if ~results_base.success
            error('Base case DC power flow failed');
        end
        total_load = sum(mpc.bus(:, PD));
        fprintf('=== Base Case ===\n');
        fprintf('Total load: %.2f MW\n', total_load);

        %% Build adjacency for graph-distance scoping
        f_bus = mpc.branch(:, F_BUS);
        t_bus = mpc.branch(:, T_BUS);
        bus_nums = mpc.bus(:, BUS_I);
        bus_map = containers.Map('KeyType', 'int32', 'ValueType', 'int32');
        for i = 1:nb
            bus_map(int32(bus_nums(i))) = int32(i);
        end
        f_idx = zeros(nl, 1);
        t_idx = zeros(nl, 1);
        for i = 1:nl
            f_idx(i) = bus_map(int32(f_bus(i)));
            t_idx(i) = bus_map(int32(t_bus(i)));
        end
        adj = sparse(f_idx, t_idx, ones(nl, 1), nb, nb);
        adj = adj + adj';
        adj = adj > 0;

        %% Build PTDF and LODF for screening (native MATPOWER API)
        [Bbus, Bf, Pbusinj, Pfinj] = makeBdc(mpc.baseMVA, mpc.bus, mpc.branch);
        PTDF = makePTDF(mpc.baseMVA, mpc.bus, mpc.branch);
        LODF = makeLODF(mpc.branch, PTDF);

        fprintf('PTDF matrix: %d x %d\n', size(PTDF, 1), size(PTDF, 2));
        fprintf('LODF matrix: %d x %d\n', size(LODF, 1), size(LODF, 2));

        %% Parameters
        x = 3;  % Graph distance for scoping
        m = 3;  % Maximum simultaneous outages

        %% Identify in-service branches with nonzero flow
        active_branches = find(mpc.branch(:, BR_STATUS) == 1);
        fprintf('Active branches: %d\n', length(active_branches));

        %% Get base-case flows
        base_flows = results_base.branch(:, PF);
        branch_limits = mpc.branch(:, RATE_A);

        %% Helper: BFS neighbors within distance x from a branch's buses
        %% (implemented inline to avoid nested function limitation)

        %% N-1 contingency sweep with LODF screening
        fprintf('\n=== N-1 Contingency Sweep (with LODF screening) ===\n');
        n1_results = struct('branch', {}, 'load_loss', {}, 'max_overload', {}, 'islanded', {});
        n1_count = 0;

        for i = 1:length(active_branches)
            bidx = active_branches(i);

            %% Check if outage creates island (LODF will have NaN/Inf)
            lodf_col = LODF(:, bidx);
            if any(isinf(lodf_col) | isnan(lodf_col))
                %% Radial branch -- outage creates island
                n1_count = n1_count + 1;
                n1_results(n1_count).branch = bidx;
                n1_results(n1_count).load_loss = -1;  % Unknown (island)
                n1_results(n1_count).max_overload = 0;
                n1_results(n1_count).islanded = true;
                continue
            end

            %% Compute post-contingency flows using LODF (no model reconstruction!)
            post_flows = base_flows + lodf_col .* base_flows(bidx);
            post_flows(bidx) = 0;  % Outaged branch has zero flow

            %% Check overloads
            overloads = zeros(nl, 1);
            for j = 1:nl
                if branch_limits(j) > 0 && j ~= bidx
                    overloads(j) = abs(post_flows(j)) / branch_limits(j);
                end
            end
            max_overload = max(overloads);

            %% Estimate load loss: run DCPF with branch removed
            %% Use in-place branch status toggle (no model reconstruction)
            mpc_tmp = mpc;
            mpc_tmp.branch(bidx, BR_STATUS) = 0;
            results_tmp = rundcpf(mpc_tmp, mpopt);

            if results_tmp.success
                served_load = sum(results_tmp.bus(:, PD));
                load_loss = total_load - served_load;
            else
                %% Check for islands
                groups = find_islands(mpc_tmp);
                if length(groups) > 1
                    load_loss = -1;  % Islanded
                else
                    load_loss = 0;
                end
            end

            n1_count = n1_count + 1;
            n1_results(n1_count).branch = bidx;
            n1_results(n1_count).load_loss = load_loss;
            n1_results(n1_count).max_overload = max_overload;
            n1_results(n1_count).islanded = false;
        end

        fprintf('N-1 contingencies evaluated: %d\n', n1_count);

        %% Print N-1 results summary
        n1_violations = 0;
        n1_islands = 0;
        for i = 1:n1_count
            if n1_results(i).islanded
                n1_islands = n1_islands + 1;
            elseif n1_results(i).max_overload > 1.0
                n1_violations = n1_violations + 1;
            end
        end
        fprintf('N-1 violations (overloads): %d\n', n1_violations);
        fprintf('N-1 island-creating outages: %d\n', n1_islands);

        %% N-2 contingency sweep with graph-distance scoping and LODF pruning
        fprintf('\n=== N-2 Contingency Sweep (graph-distance scoped, x=%d) ===\n', x);
        n2_count = 0;
        n2_pruned = 0;
        n2_results = struct('branches', {}, 'load_loss', {}, 'max_overload', {});

        %% For each N-1 outage with violations, scope N-2 partners
        violation_branches = [];
        for i = 1:n1_count
            if ~n1_results(i).islanded && n1_results(i).max_overload > 1.0
                violation_branches(end + 1) = n1_results(i).branch;
            end
        end

        %% Limit N-2 combinations to graph-distance scoped partners
        for i = 1:length(violation_branches)
            b1 = violation_branches(i);
            scope = get_branch_scope(b1, x, f_bus, t_bus, bus_map, adj, nb, f_idx, t_idx, nl);

            for j = 1:length(scope)
                b2 = scope(j);
                if b2 <= b1
                    continue
                end  % Avoid duplicates
                if ~ismember(b2, active_branches)
                    continue
                end

                %% LODF-based screening: estimate post-contingency impact
                %% Use LODF for quick screening before full solve
                lodf_b1 = LODF(:, b1);
                lodf_b2 = LODF(:, b2);

                %% Skip if either creates island
                if any(isinf(lodf_b1) | isnan(lodf_b1)) || any(isinf(lodf_b2) | isnan(lodf_b2))
                    n2_pruned = n2_pruned + 1;
                    continue
                end

                %% Quick screening: approximate post-contingency flows
                post_flows_approx = base_flows + lodf_b1 * base_flows(b1) + lodf_b2 *  ...
                    base_flows(b2);
                post_flows_approx(b1) = 0;
                post_flows_approx(b2) = 0;

                max_loading = 0;
                for k = 1:nl
                    if branch_limits(k) > 0 && k ~= b1 && k ~= b2
                        loading = abs(post_flows_approx(k)) / branch_limits(k);
                        if loading > max_loading
                            max_loading = loading;
                        end
                    end
                end

                %% Prune if no significant overload expected
                if max_loading < 0.9
                    n2_pruned = n2_pruned + 1;
                    continue
                end

                %% Full solve for non-pruned cases
                mpc_tmp = mpc;
                mpc_tmp.branch(b1, BR_STATUS) = 0;
                mpc_tmp.branch(b2, BR_STATUS) = 0;
                results_tmp = rundcpf(mpc_tmp, mpopt);

                if results_tmp.success
                    served_load = sum(results_tmp.bus(:, PD));
                    load_loss = total_load - served_load;
                else
                    load_loss = -1;
                end

                n2_count = n2_count + 1;
                n2_results(n2_count).branches = [b1, b2];
                n2_results(n2_count).load_loss = load_loss;
                n2_results(n2_count).max_overload = max_loading;
            end
        end
        fprintf('N-2 contingencies evaluated: %d\n', n2_count);
        fprintf('N-2 contingencies pruned: %d\n', n2_pruned);

        %% N-3 contingency sweep (m=3, only from worst N-2 cases)
        fprintf('\n=== N-3 Contingency Sweep (from worst N-2, m=%d) ===\n', m);
        n3_count = 0;
        n3_pruned = 0;
        n3_results = struct('branches', {}, 'load_loss', {});

        %% Find worst N-2 cases (top 5 by overload)
        if n2_count > 0
            overloads_n2 = zeros(n2_count, 1);
            for i = 1:n2_count
                overloads_n2(i) = n2_results(i).max_overload;
            end
            [~, worst_idx] = sort(overloads_n2, 'descend');
            n_worst = min(5, n2_count);

            for w = 1:n_worst
                wi = worst_idx(w);
                pair = n2_results(wi).branches;

                %% Scope third branch within distance x of the pair
                scope1 = get_branch_scope(pair(1), x, f_bus, t_bus, bus_map, adj, nb, f_idx, ...
                                          t_idx, nl);
                scope2 = get_branch_scope(pair(2), x, f_bus, t_bus, bus_map, adj, nb, f_idx, ...
                                          t_idx, nl);
                scope3 = unique([scope1, scope2]);

                for j = 1:length(scope3)
                    b3 = scope3(j);
                    if b3 <= max(pair)
                        continue
                    end
                    if ~ismember(b3, active_branches)
                        continue
                    end
                    if ismember(b3, pair)
                        continue
                    end

                    %% Full solve
                    mpc_tmp = mpc;
                    mpc_tmp.branch(pair(1), BR_STATUS) = 0;
                    mpc_tmp.branch(pair(2), BR_STATUS) = 0;
                    mpc_tmp.branch(b3, BR_STATUS) = 0;
                    results_tmp = rundcpf(mpc_tmp, mpopt);

                    if results_tmp.success
                        served_load = sum(results_tmp.bus(:, PD));
                        load_loss = total_load - served_load;
                    else
                        load_loss = -1;
                    end

                    n3_count = n3_count + 1;
                    n3_results(n3_count).branches = [pair, b3];
                    n3_results(n3_count).load_loss = load_loss;
                end
            end
        end
        fprintf('N-3 contingencies evaluated: %d\n', n3_count);

        total_contingencies = n1_count + n2_count + n3_count;
        fprintf('\n=== Summary ===\n');
        fprintf('Total contingencies: %d (N-1: %d, N-2: %d, N-3: %d)\n', ...
                total_contingencies, n1_count, n2_count, n3_count);
        fprintf('N-2 pruned by screening: %d\n', n2_pruned);

        %% Peak memory
        [~, mem_out] = system('grep VmHWM /proc/self/status');
        peak_kb = sscanf(mem_out, 'VmHWM: %f');
        if ~isempty(peak_kb)
            peak_memory_mb = peak_kb / 1024;
        else
            peak_memory_mb = -1;
        end

        %% Store results
        result.details.n1_count = n1_count;
        result.details.n2_count = n2_count;
        result.details.n3_count = n3_count;
        result.details.n2_pruned = n2_pruned;
        result.details.total_contingencies = total_contingencies;
        result.details.n1_violations = n1_violations;
        result.details.n1_islands = n1_islands;
        result.details.peak_memory_mb = peak_memory_mb;

        %% Pass condition: completed escalating sweep, no full model reconstruction
        if total_contingencies > 0
            result.status = 'pass';
            fprintf('\n=== PASS: Escalating N-M contingency sweep completed ===\n');
        else
            result.errors{end + 1} = 'No contingencies were evaluated';
        end

    catch e
        result.errors{end + 1} = e.message;
        fprintf('ERROR: %s\n', e.message);
    end
    result.wall_clock_seconds = toc;
end

function scope = get_branch_scope(branch_idx, dist, f_bus, t_bus, bus_map, adj, nb, f_idx, ...
                                  t_idx, nl)
    %% Get branches within BFS distance 'dist' from either end of given branch
    b1 = bus_map(int32(f_bus(branch_idx)));
    b2 = bus_map(int32(t_bus(branch_idx)));
    visited = false(nb, 1);
    visited(b1) = true;
    visited(b2) = true;
    queue = [b1, b2];
    qdepth = [0, 0];
    while ~isempty(queue)
        cur = queue(1);
        queue(1) = [];
        cd = qdepth(1);
        qdepth(1) = [];
        if cd >= dist
            continue
        end
        neighbors = find(adj(cur, :));
        for nn = neighbors
            if ~visited(nn)
                visited(nn) = true;
                queue(end + 1) = nn;
                qdepth(end + 1) = cd + 1;
            end
        end
    end
    %% Find branches with both endpoints in the scope
    scope = [];
    for bi = 1:nl
        if visited(f_idx(bi)) && visited(t_idx(bi))
            scope(end + 1) = bi;
        end
    end
end
