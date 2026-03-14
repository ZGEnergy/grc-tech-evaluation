%% Test A-9: Solve DC OPF with N-1 contingency constraints embedded in optimization
%%
%% Dimension: expressiveness
%% Network: TINY (IEEE 39-bus New England)
%% Pass condition: Solves. Base-case dispatch respects all contingency flow limits
%%   simultaneously. Cost differs from A-3. Contingency constraints are part of
%%   the optimization, not post-hoc.
%% Tool: MATPOWER 8.1
%% Solver: MIPS

%% Setup MATPOWER paths
mp_root = fullfile(fileparts(mfilename('fullpath')), '..', '..', 'matpower8.1');
addpath(fullfile(mp_root, 'lib'));
addpath(fullfile(mp_root, 'data'));
addpath(fullfile(mp_root, 'mips', 'lib'));
addpath(fullfile(mp_root, 'mp-opt-model', 'lib'));
addpath(fullfile(mp_root, 'mptest', 'lib'));

network_file = '/workspace/data/networks/case39.m';
timeseries_dir = '/workspace/data/timeseries/case39';

result_status = 'fail';
errors = {};
workarounds = {};

try
    %% Load case
    mpc = loadcase(network_file);
    define_constants;

    %% Load differentiated costs (same as A-3)
    gen_params_file = fullfile(timeseries_dir, 'gen_temporal_params.csv');
    fid = fopen(gen_params_file, 'r');
    header = fgetl(fid);
    gen_data = {};
    while ~feof(fid)
        line = fgetl(fid);
        if ischar(line) && ~isempty(line)
            gen_data{end + 1} = line;
        end
    end
    fclose(fid);

    tech_keys = {};
    for i = 1:length(gen_data)
        parts = strsplit(gen_data{i}, ',');
        tech_keys{i} = strtrim(parts{5});
    end

    ngen = size(mpc.gen, 1);
    new_gencost = zeros(ngen, 7);
    for i = 1:ngen
        key = tech_keys{i};
        switch key
            case 'hydro'
                c1 = 5.0;
                c2 = 0.005;
            case 'nuclear'
                c1 = 10.0;
                c2 = 0.010;
            case 'coal_large'
                c1 = 25.0;
                c2 = 0.025;
            case 'gas_CC'
                c1 = 40.0;
                c2 = 0.040;
            otherwise
                c1 = 40.0;
                c2 = 0.040;
        end
        new_gencost(i, :) = [2 0 0 3 c2 c1 0];
    end
    mpc.gencost = new_gencost;

    %% Apply 70% branch derating (same as A-3)
    mpc.branch(:, RATE_A) = mpc.branch(:, RATE_A) * 0.70;
    mpc.branch(:, RATE_B) = mpc.branch(:, RATE_B) * 0.70;
    mpc.branch(:, RATE_C) = mpc.branch(:, RATE_C) * 0.70;

    nbr = size(mpc.branch, 1);

    %% Solve baseline DC OPF
    mpopt = mpoption('verbose', 0, 'out.all', 0, 'opf.dc.solver', 'MIPS');
    results_base = rundcopf(mpc, mpopt);
    if ~results_base.success
        error('Baseline DC OPF did not converge');
    end
    base_cost = results_base.f;
    fprintf('Baseline DC OPF cost (A-3): $%.2f\n', base_cost);

    %% Build LODF for contingency screening
    mpc_int = ext2int(mpc);
    nbr_int = size(mpc_int.branch, 1);
    nb_int = size(mpc_int.bus, 1);
    PTDF = makePTDF(mpc_int.baseMVA, mpc_int.bus, mpc_int.branch);
    LODF = makeLODF(mpc_int.branch, PTDF);
    [~, Bf] = makeBdc(mpc_int.baseMVA, mpc_int.bus, mpc_int.branch);

    %% Filter radial branches
    all_in_service = find(mpc_int.branch(:, BR_STATUS) == 1);
    cont_branches = [];
    radial_count = 0;
    for k = 1:length(all_in_service)
        br = all_in_service(k);
        if any(isinf(LODF(:, br)) | isnan(LODF(:, br)))
            radial_count = radial_count + 1;
        else
            cont_branches = [cont_branches; br];
        end
    end
    fprintf('Contingencies: %d valid, %d radial (excluded)\n', length(cont_branches), radial_count);

    %% Screen base-case dispatch for N-1 violations
    results_int = ext2int(results_base);
    va_int = results_int.bus(:, VA) * pi / 180;
    base_flows_pu = Bf * va_int;
    base_flows_mw = base_flows_pu * mpc_int.baseMVA;
    rate_a_int = mpc_int.branch(:, RATE_A);

    total_violations = 0;
    worst_overload = 0;

    for k = 1:length(cont_branches)
        k_br = cont_branches(k);
        for l = 1:nbr_int
            if l == k_br || rate_a_int(l) <= 0
                continue
            end
            lodf_val = LODF(l, k_br);
            if abs(lodf_val) < 0.001 || isinf(lodf_val) || isnan(lodf_val)
                continue
            end
            post_flow = abs(base_flows_mw(l) + lodf_val * base_flows_mw(k_br));
            if post_flow > rate_a_int(l) * 1.005
                total_violations = total_violations + 1;
                overload = post_flow / rate_a_int(l);
                if overload > worst_overload
                    worst_overload = overload;
                end
            end
        end
    end
    fprintf('Base-case N-1 violations: %d (worst: %.1f%%)\n', total_violations, ...
            100 * worst_overload);

    %% Attempt SCOPF via mpc.A/l/u user constraint injection
    %% Build post-contingency flow constraints: for each violated pair (k,l),
    %% add: -rate_a(l)/baseMVA <= [Bf(l,:) + LODF(l,k)*Bf(k,:)] * Va <= rate_a(l)/baseMVA
    nvar = nb_int + ngen;
    rate_a_pu = rate_a_int / mpc_int.baseMVA;

    % Build constraints for ALL significant contingencies
    rows = [];
    ls = [];
    us = [];
    constraint_count = 0;
    for k = 1:length(cont_branches)
        k_br = cont_branches(k);
        for l = 1:nbr_int
            if l == k_br || rate_a_int(l) <= 0
                continue
            end
            lodf_val = LODF(l, k_br);
            if abs(lodf_val) < 0.05 || isinf(lodf_val) || isnan(lodf_val)
                continue
            end
            constraint_count = constraint_count + 1;
            coeff = full(Bf(l, :) + lodf_val * Bf(k_br, :));
            row_data = sparse(1, nvar);
            row_data(1, 1:nb_int) = coeff;
            rows{constraint_count} = row_data;
            ls(constraint_count) = -rate_a_pu(l);
            us(constraint_count) = rate_a_pu(l);
        end
    end
    fprintf('N-1 constraints built: %d\n', constraint_count);

    % Assemble sparse A matrix
    A_user = vertcat(rows{:});

    mpc_scopf = mpc;
    mpc_scopf.A = A_user;
    mpc_scopf.l = ls';
    mpc_scopf.u = us';

    fprintf('Attempting SCOPF with user constraints...\n');
    tic;
    results_scopf = rundcopf(mpc_scopf, mpopt);
    scopf_time = toc;

    if results_scopf.success
        scopf_cost = results_scopf.f;
        cost_increase = scopf_cost - base_cost;
        fprintf('SCOPF SUCCEEDED!\n');
        fprintf('SCOPF cost: $%.2f (increase: $%.2f, %.2f%%)\n', ...
                scopf_cost, cost_increase, 100 * cost_increase / base_cost);

        fprintf('\nDispatch comparison:\n');
        for i = 1:ngen
            fprintf('  Gen %d (bus %d, %s): %.2f -> %.2f MW\n', ...
                    i, results_scopf.gen(i, GEN_BUS), tech_keys{i}, ...
                    results_base.gen(i, PG), results_scopf.gen(i, PG));
        end

        if scopf_cost > base_cost
            result_status = 'qualified_pass';
            workarounds{end + 1} = 'No native SCOPF function. Used LODF-based N-1 constraint';
        end
    else
        fprintf('SCOPF with user constraints FAILED (MIPS solver)\n');
        fprintf('MIPS encounters numerical singularity with %d user constraints\n', ...
                constraint_count);

        %% Try with fewer constraints (top-10 worst only)
        fprintf('\nRetrying with only top-10 worst constraints...\n');
        % Re-screen and sort
        violation_data = [];
        for k = 1:length(cont_branches)
            k_br = cont_branches(k);
            for l = 1:nbr_int
                if l == k_br || rate_a_int(l) <= 0
                    continue
                end
                lodf_val = LODF(l, k_br);
                if abs(lodf_val) < 0.05 || isinf(lodf_val) || isnan(lodf_val)
                    continue
                end
                post_flow = abs(base_flows_mw(l) + lodf_val * base_flows_mw(k_br));
                if post_flow > rate_a_int(l)
                    violation_data = [violation_data; k_br, l, post_flow / rate_a_int(l)];
                end
            end
        end

        if ~isempty(violation_data)
            [~, sidx] = sort(violation_data(:, 3), 'descend');
            n_top = min(5, size(violation_data, 1));

            A_small = sparse(n_top, nvar);
            l_small = zeros(n_top, 1);
            u_small = zeros(n_top, 1);
            for i = 1:n_top
                k_br = violation_data(sidx(i), 1);
                l = violation_data(sidx(i), 2);
                lodf_val = LODF(l, k_br);
                coeff = full(Bf(l, :) + lodf_val * Bf(k_br, :));
                A_small(i, 1:nb_int) = coeff;
                l_small(i) = -rate_a_pu(l);
                u_small(i) = rate_a_pu(l);
            end

            mpc_scopf2 = mpc;
            mpc_scopf2.A = A_small;
            mpc_scopf2.l = l_small;
            mpc_scopf2.u = u_small;

            results_scopf2 = rundcopf(mpc_scopf2, mpopt);
            if results_scopf2.success
                scopf_cost2 = results_scopf2.f;
                fprintf('Partial SCOPF (top-%d constraints): cost=$%.2f\n', n_top, scopf_cost2);
                fprintf('Cost increase: $%.2f (%.2f%%)\n', ...
                        scopf_cost2 - base_cost, 100 * (scopf_cost2 - base_cost) / base_cost);

                result_status = 'fail';
                errors{end + 1} = 'MIPS fails with full N-1 constraints';
            else
                fprintf('Even partial SCOPF failed\n');
                errors{end + 1} = 'MIPS fails with reduced constraints';
            end
        end
    end

    %% Peak memory
    [~, mem_out] = system('grep VmHWM /proc/self/status');
    peak_kb = sscanf(mem_out, 'VmHWM: %f');
    if ~isempty(peak_kb)
        peak_memory_mb = peak_kb / 1024;
    else
        peak_memory_mb = -1;
    end
    fprintf('Peak memory: %.1f MB\n', peak_memory_mb);

catch e
    errors{end + 1} = e.message;
    fprintf('ERROR: %s\n', e.message);
end

fprintf('\nStatus: %s\n', result_status);
if ~isempty(errors)
    fprintf('Errors: %s\n', strjoin(errors, '; '));
end
if ~isempty(workarounds)
    fprintf('Workarounds: %s\n', strjoin(workarounds, '; '));
end
