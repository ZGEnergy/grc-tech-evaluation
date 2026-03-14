%% Test A-3: Solve DC OPF with differentiated gen costs and 70% branch derating on TINY
%%
%% Dimension: expressiveness
%% Network: TINY (IEEE 39-bus New England)
%% Pass condition: Converges. Optimal dispatch and LMPs/shadow prices extractable.
%%   With differentiated costs and 70% derating, at least 2 branches have non-zero
%%   shadow prices (binding flow constraints). Report max LMP spread across buses.
%% Tool: MATPOWER 8.1
%% Solver: HiGHS

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
solver_used = 'unknown';

try
    %% Load case
    mpc = loadcase(network_file);
    define_constants;

    %% Load differentiated costs from gen_temporal_params.csv
    gen_params_file = fullfile(timeseries_dir, 'gen_temporal_params.csv');
    fid = fopen(gen_params_file, 'r');
    if fid == -1
        error('Cannot open %s', gen_params_file);
    end
    header = fgetl(fid);
    gen_data = {};
    while ~feof(fid)
        line = fgetl(fid);
        if ischar(line) && ~isempty(line)
            gen_data{end + 1} = line;
        end
    end
    fclose(fid);

    % Parse tech_class_key (column 5, 1-indexed)
    tech_keys = {};
    for i = 1:length(gen_data)
        parts = strsplit(gen_data{i}, ',');
        tech_keys{i} = strtrim(parts{5});
    end

    % Cost map: tech_class_key -> [c1 ($/MWh), c2 ($/MW^2h)]
    % cost = c2*Pg^2 + c1*Pg + c0
    ngen = size(mpc.gen, 1);

    % Ensure gencost has enough columns for quadratic (7 columns)
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
        % Polynomial type=2, startup=0, shutdown=0, ncost=3, c2, c1, c0
        new_gencost(i, :) = [2 0 0 3 c2 c1 0];
    end
    mpc.gencost = new_gencost;

    %% Apply 70% branch derating
    mpc.branch(:, RATE_A) = mpc.branch(:, RATE_A) * 0.70;
    mpc.branch(:, RATE_B) = mpc.branch(:, RATE_B) * 0.70;
    mpc.branch(:, RATE_C) = mpc.branch(:, RATE_C) * 0.70;

    %% Check if HiGHS is available
    highs_available = have_feature('highs');
    fprintf('HiGHS available: %d\n', highs_available);

    %% Configure solver
    if highs_available
        mpopt = mpoption('verbose', 0, 'out.all', 0, 'opf.dc.solver', 'HIGHS');
        solver_used = 'HiGHS';
    else
        fprintf('HiGHS not available, using MIPS (built-in)\n');
        mpopt = mpoption('verbose', 0, 'out.all', 0, 'opf.dc.solver', 'MIPS');
        solver_used = 'MIPS';
        workarounds{end + 1} = 'HiGHS solver not available; using MIPS (built-in)';
    end

    %% Solve DC OPF
    tic;
    results = rundcopf(mpc, mpopt);
    solve_time = toc;

    if ~results.success
        errors{end + 1} = sprintf('DC OPF did not converge with %s', solver_used);

        %% Try fallback to GLPK if primary solver failed
        if ~strcmp(solver_used, 'MIPS')
            fprintf('Primary solver failed, trying MIPS...\n');
            mpopt_fb = mpoption('verbose', 0, 'out.all', 0, 'opf.dc.solver', 'MIPS');
            tic;
            results = rundcopf(mpc, mpopt_fb);
            solve_time = toc;
            if results.success
                solver_used = 'MIPS (fallback)';
                workarounds{end + 1} = sprintf('Primary solver failed; fell back to MIPS');
                errors = {};
            end
        end
    end

    if results.success
        %% Extract results
        bus_count = size(results.bus, 1);
        branch_count = size(results.branch, 1);

        % LMPs
        lmps = results.bus(:, LAM_P);
        lmp_max = max(lmps);
        lmp_min = min(lmps);
        lmp_spread = lmp_max - lmp_min;

        % Shadow prices on branch flow limits
        mu_sf = results.branch(:, MU_SF);
        mu_st = results.branch(:, MU_ST);
        binding_branches = (abs(mu_sf) > 1e-4) | (abs(mu_st) > 1e-4);
        binding_count = sum(binding_branches);

        % Generator dispatch
        gen_pg = results.gen(:, PG);
        gen_buses = results.gen(:, GEN_BUS);

        % Objective value
        obj_value = results.f;

        %% Peak memory
        [~, mem_out] = system('grep VmHWM /proc/self/status');
        peak_kb = sscanf(mem_out, 'VmHWM: %f');
        if ~isempty(peak_kb)
            peak_memory_mb = peak_kb / 1024;
        else
            peak_memory_mb = -1;
        end

        %% Print results
        fprintf('\n=== Test A-3: DC OPF Results ===\n');
        fprintf('Wall clock: %.4f s\n', solve_time);
        fprintf('Solver: %s\n', solver_used);
        fprintf('Objective value: $%.2f\n', obj_value);
        fprintf('Total generation: %.2f MW\n', sum(gen_pg));
        fprintf('Total load: %.2f MW\n', sum(results.bus(:, PD)));
        fprintf('LMP range: [%.4f, %.4f] $/MWh, spread: %.4f\n', lmp_min, lmp_max, lmp_spread);
        fprintf('LMP mean: %.4f $/MWh\n', mean(lmps));
        fprintf('Binding branches: %d\n', binding_count);
        fprintf('Branch derating: 70%%\n');
        fprintf('Peak memory: %.1f MB\n', peak_memory_mb);

        % Print binding branch details
        binding_idx = find(binding_branches);
        if ~isempty(binding_idx)
            fprintf('\nBinding branch details:\n');
            fprintf('  From -> To  | mu_sf     | mu_st     | Flow (MW)\n');
            for i = 1:length(binding_idx)
                idx = binding_idx(i);
                fprintf('  %3d -> %3d | %9.4f | %9.4f | %9.2f\n', ...
                        results.branch(idx, F_BUS), results.branch(idx, T_BUS), ...
                        mu_sf(idx), mu_st(idx), results.branch(idx, PF));
            end
        end

        % Print dispatch
        fprintf('\nGenerator dispatch:\n');
        fprintf('  Bus | Tech     | Dispatch (MW) | Pmax (MW)\n');
        for i = 1:ngen
            fprintf('  %3d | %-8s | %12.2f  | %9.2f\n', ...
                    gen_buses(i), tech_keys{i}, gen_pg(i), results.gen(i, PMAX));
        end

        % Print LMPs per bus (all buses)
        fprintf('\nBus LMPs:\n');
        fprintf('  Bus | LMP ($/MWh) | Load (MW)\n');
        for i = 1:bus_count
            fprintf('  %3d | %11.4f | %9.2f\n', ...
                    results.bus(i, BUS_I), lmps(i), results.bus(i, PD));
        end

        %% Pass condition check
        if binding_count >= 2 && lmp_spread > 0
            result_status = 'pass';
        else
            if binding_count < 2
                errors{end + 1} = sprintf('Only %d binding branches (need >= 2)', binding_count);
            end
            if lmp_spread <= 0
                errors{end + 1} = 'No LMP spread (all buses have same price)';
            end
        end
    end

catch e
    errors{end + 1} = e.message;
end

fprintf('\nStatus: %s\n', result_status);
if ~isempty(errors)
    fprintf('Errors: %s\n', strjoin(errors, '; '));
end
if ~isempty(workarounds)
    fprintf('Workarounds: %s\n', strjoin(workarounds, '; '));
end
