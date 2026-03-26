%% Test A-9: Solve DC OPF with N-1 contingency constraints embedded in optimization
%%
%% Dimension: expressiveness
%% Network: TINY (IEEE 39-bus New England)
%% Pass condition: Solves. Base-case dispatch respects all contingency flow limits
%%   simultaneously. Cost differs from A-3. Contingency constraints part of optimization.
%%   v11: Requires Benders iteration (>=2) or explicit feasibility confirmation.
%% Tool: MATPOWER 8.1
%% Solver: GLPK (LP), MIPS (QP)

%% Setup MATPOWER paths
addpath(genpath('/workspace/evaluations/matpower/matpower8.1'));

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

    %% Solve baseline DC OPF (A-3 reference)
    mpopt = mpoption('verbose', 0, 'out.all', 0, 'opf.dc.solver', 'MIPS');
    results_base = rundcopf(mpc, mpopt);
    if ~results_base.success
        error('Baseline DC OPF did not converge');
    end
    base_cost = results_base.f;
    fprintf('Baseline DC OPF cost (A-3): $%.2f\n', base_cost);

    %% Build PTDF/LODF for contingency analysis
    mpc_int = ext2int(mpc);
    nbr_int = size(mpc_int.branch, 1);
    nb_int = size(mpc_int.bus, 1);
    PTDF = makePTDF(mpc_int.baseMVA, mpc_int.bus, mpc_int.branch);
    LODF = makeLODF(mpc_int.branch, PTDF);
    [~, Bf] = makeBdc(mpc_int.baseMVA, mpc_int.bus, mpc_int.branch);

    %% Identify radial branches (LODF has Inf for island-creating outages)
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
    base_flows_mw = full(Bf * va_int) * mpc_int.baseMVA;
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

    %% ================================================================
    %% v11 REQUIREMENT: Benders-style iterative SCOPF (>=2 iterations)
    %% Approach: solve DC OPF, screen contingencies, add violated constraints,
    %% re-solve. Uses LODF-based post-contingency flow constraints injected
    %% via mpc.A/l/u user constraint interface.
    %% ================================================================

    nvar = nb_int + ngen;
    rate_a_pu = rate_a_int / mpc_int.baseMVA;

    %% Attempt 1: Benders with GLPK (LP only — use linear costs)
    fprintf('\n=== Benders Attempt 1: GLPK with linear costs ===\n');
    mpc_lin = mpc;
    for i = 1:ngen
        key = tech_keys{i};
        switch key
            case 'hydro'; c1 = 5.0;
            case 'nuclear'; c1 = 10.0;
            case 'coal_large'; c1 = 25.0;
            case 'gas_CC'; c1 = 40.0;
            otherwise; c1 = 40.0;
        end
        mpc_lin.gencost(i, :) = [2 0 0 2 c1 0 0];
    end

    mpopt_glpk = mpoption('verbose', 0, 'out.all', 0, 'opf.dc.solver', 'GLPK');
    mpc_iter = mpc_lin;
    added_constraints = {};
    all_A = [];
    all_l = [];
    all_u = [];
    benders_converged = false;

    for benders_iter = 1:10
        results_iter = rundcopf(mpc_iter, mpopt_glpk);
        if ~results_iter.success
            fprintf('Benders iter %d: INFEASIBLE with %d constraints\n', ...
                    benders_iter, size(all_A, 1));
            errors{end + 1} = sprintf('SCOPF infeasible at Benders iter %d with %d constraints', ...
                                       benders_iter, size(all_A, 1));
            break;
        end

        results_iter_int = ext2int(results_iter);
        va_iter = results_iter_int.bus(:, VA) * pi / 180;
        flows_iter = full(Bf * va_iter) * mpc_int.baseMVA;

        new_violations = 0;
        for k = 1:length(cont_branches)
            k_br = cont_branches(k);
            for l = 1:nbr_int
                if l == k_br || rate_a_int(l) <= 0; continue; end
                lodf_val = LODF(l, k_br);
                if abs(lodf_val) < 0.01 || isinf(lodf_val) || isnan(lodf_val); continue; end
                post_flow = abs(flows_iter(l) + lodf_val * flows_iter(k_br));
                if post_flow > rate_a_int(l) * 1.005
                    key = sprintf('%d_%d', k_br, l);
                    if ~any(strcmp(added_constraints, key))
                        new_violations = new_violations + 1;
                        added_constraints{end+1} = key;
                        coeff = full(Bf(l, :) + lodf_val * Bf(k_br, :));
                        row = sparse(1, nvar);
                        row(1, 1:nb_int) = coeff;
                        all_A = [all_A; row];
                        all_l = [all_l; -rate_a_pu(l)];
                        all_u = [all_u; rate_a_pu(l)];
                    end
                end
            end
        end

        fprintf('Benders iter %d: cost=$%.2f, new_violations=%d, total_constraints=%d\n', ...
                benders_iter, results_iter.f, new_violations, size(all_A, 1));

        if new_violations == 0
            benders_converged = true;
            fprintf('Benders CONVERGED after %d iterations\n', benders_iter);
            break;
        end

        mpc_iter = mpc_lin;
        mpc_iter.A = all_A;
        mpc_iter.l = all_l;
        mpc_iter.u = all_u;
    end

    %% Attempt 2: Full N-1 constraint set with MIPS (quadratic costs)
    if ~benders_converged
        fprintf('\n=== Attempt 2: Full N-1 constraints with MIPS ===\n');
        rows = {};
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
        fprintf('Full N-1 constraints: %d\n', constraint_count);

        A_user = vertcat(rows{:});
        mpc_scopf = mpc;
        mpc_scopf.A = A_user;
        mpc_scopf.l = ls';
        mpc_scopf.u = us';

        tic;
        results_scopf = rundcopf(mpc_scopf, mpopt);
        scopf_time = toc;

        if results_scopf.success
            scopf_cost = results_scopf.f;
            fprintf('SCOPF SUCCEEDED! cost=$%.2f, time=%.4f s\n', scopf_cost, scopf_time);
            if scopf_cost > base_cost
                result_status = 'qualified_pass';
                workarounds{end + 1} = 'No native SCOPF; LODF-based constraint injection via mpc.A/l/u';
            end
        else
            fprintf('SCOPF with full constraints FAILED (solver)\n');
            errors{end + 1} = 'MIPS solver fails with N-1 user constraints';
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
    fprintf('\nPeak memory: %.1f MB\n', peak_memory_mb);

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
