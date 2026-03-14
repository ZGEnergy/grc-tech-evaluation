%% Test A-4: Take DC OPF dispatch from A-3, run full ACPF on that dispatch
%%
%% Dimension: expressiveness
%% Network: TINY (IEEE 39-bus New England)
%% Pass condition: Achievable within the same model context (no export to file
%%   and reimport). Voltage violations and thermal limit violations identifiable.
%% Tool: MATPOWER 8.1
%% Solver: MIPS (DC OPF), Newton-Raphson (ACPF)

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

    %% Load differentiated costs from gen_temporal_params.csv (same as A-3)
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

    %% Step 1: Solve DC OPF (same as A-3)
    mpopt_dc = mpoption('verbose', 0, 'out.all', 0, 'opf.dc.solver', 'MIPS');
    tic;
    results_dc = rundcopf(mpc, mpopt_dc);
    dc_time = toc;

    if ~results_dc.success
        error('DC OPF did not converge');
    end

    fprintf('DC OPF converged in %.4f s\n', dc_time);
    fprintf('DC OPF objective: $%.2f\n', results_dc.f);

    %% Step 2: Set generator dispatch from DC OPF into the case for AC PF
    %% This is done IN THE SAME MODEL CONTEXT -- no file export/reimport
    mpc_ac = results_dc;  % Start from DC OPF result struct (contains all mpc fields)

    % Set generator active power to DC OPF dispatch
    % (already set in results_dc.gen(:, PG))
    fprintf('\nDC OPF dispatch transferred to AC PF (in-memory, no file I/O):\n');
    for i = 1:ngen
        fprintf('  Gen %d (bus %d, %s): PG = %.2f MW\n', ...
                i, mpc_ac.gen(i, GEN_BUS), tech_keys{i}, mpc_ac.gen(i, PG));
    end

    % Reset voltage magnitudes to flat start for AC PF
    mpc_ac.bus(:, VM) = 1.0;
    mpc_ac.bus(:, VA) = 0.0;

    %% Step 3: Run AC Power Flow with the DC dispatch
    mpopt_ac = mpoption('verbose', 0, 'out.all', 0, ...
                        'pf.alg', 'NR', 'pf.tol', 1e-8, 'pf.nr.max_it', 50, ...
                        'pf.enforce_q_lims', 1);

    tic;
    results_ac = runpf(mpc_ac, mpopt_ac);
    ac_time = toc;

    total_time = dc_time + ac_time;

    if ~results_ac.success
        errors{end + 1} = 'AC PF did not converge with DC OPF dispatch';
        fprintf('AC PF FAILED to converge\n');
    else
        fprintf('AC PF converged in %.4f s\n', ac_time);
    end

    %% Step 4: Identify voltage violations
    vm = results_ac.bus(:, VM);
    vmax_lim = results_ac.bus(:, VMAX);
    vmin_lim = results_ac.bus(:, VMIN);

    v_over = vm > vmax_lim;
    v_under = vm < vmin_lim;
    v_violations = v_over | v_under;
    n_v_violations = sum(v_violations);

    % Also check wider bands
    v_over_strict = vm > 1.05;
    v_under_strict = vm < 0.95;
    v_violations_strict = v_over_strict | v_under_strict;
    n_v_violations_strict = sum(v_violations_strict);

    fprintf('\n=== Voltage Analysis ===\n');
    fprintf('VM range: [%.4f, %.4f] p.u.\n', min(vm), max(vm));
    fprintf('Buses with VM outside [Vmin, Vmax]: %d\n', n_v_violations);
    fprintf('Buses with VM outside [0.95, 1.05]: %d\n', n_v_violations_strict);

    if n_v_violations > 0
        fprintf('\nVoltage violation details:\n');
        viol_idx = find(v_violations);
        for i = 1:length(viol_idx)
            idx = viol_idx(i);
            fprintf('  Bus %d: VM = %.4f (limits [%.4f, %.4f])\n', ...
                    results_ac.bus(idx, BUS_I), vm(idx), vmin_lim(idx), vmax_lim(idx));
        end
    end

    %% Step 5: Identify thermal violations
    % Compute apparent power flows (MVA)
    pf = results_ac.branch(:, PF);
    qf = results_ac.branch(:, QF);
    pt = results_ac.branch(:, PT);
    qt = results_ac.branch(:, QT);
    sf = sqrt(pf.^2 + qf.^2);  % MVA from-end
    st = sqrt(pt.^2 + qt.^2);  % MVA to-end
    s_max = max(sf, st);

    rate_a = results_ac.branch(:, RATE_A);
    % Thermal violations where flow exceeds rate A (already derated)
    thermal_viol = (s_max > rate_a) & (rate_a > 0);
    n_thermal_viol = sum(thermal_viol);

    fprintf('\n=== Thermal Analysis ===\n');
    fprintf('Branches with S > RATE_A: %d\n', n_thermal_viol);

    if n_thermal_viol > 0
        fprintf('\nThermal violation details:\n');
        therm_idx = find(thermal_viol);
        for i = 1:length(therm_idx)
            idx = therm_idx(i);
            fprintf('  Branch %d->%d: S = %.2f MVA, RATE_A = %.2f MVA (%.1f%%)\n', ...
                    results_ac.branch(idx, F_BUS), results_ac.branch(idx, T_BUS), ...
                    s_max(idx), rate_a(idx), 100 * s_max(idx) / rate_a(idx));
        end
    end

    %% Step 6: Q limit violations
    qg = results_ac.gen(:, QG);
    qmax = results_ac.gen(:, QMAX);
    qmin = results_ac.gen(:, QMIN);
    q_over = qg > qmax + 0.01;
    q_under = qg < qmin - 0.01;
    q_violations = q_over | q_under;
    n_q_violations = sum(q_violations);

    fprintf('\n=== Reactive Power Analysis ===\n');
    fprintf('Generators with Q outside limits: %d\n', n_q_violations);
    for i = 1:ngen
        fprintf('  Gen %d (bus %d): QG = %.2f MVAr [%.2f, %.2f]\n', ...
                i, results_ac.gen(i, GEN_BUS), qg(i), qmin(i), qmax(i));
    end

    %% Losses
    total_gen = sum(results_ac.gen(:, PG));
    total_load = sum(results_ac.bus(:, PD));
    total_losses = total_gen - total_load;
    loss_pct = 100 * total_losses / total_load;
    fprintf('\n=== Loss Summary ===\n');
    fprintf('Total generation: %.2f MW\n', total_gen);
    fprintf('Total load: %.2f MW\n', total_load);
    fprintf('Total losses: %.2f MW (%.2f%%)\n', total_losses, loss_pct);

    %% Peak memory
    [~, mem_out] = system('grep VmHWM /proc/self/status');
    peak_kb = sscanf(mem_out, 'VmHWM: %f');
    if ~isempty(peak_kb)
        peak_memory_mb = peak_kb / 1024;
    else
        peak_memory_mb = -1;
    end

    fprintf('\n=== Summary ===\n');
    fprintf('Total wall clock: %.4f s (DC: %.4f, AC: %.4f)\n', total_time, dc_time, ac_time);
    fprintf('Peak memory: %.1f MB\n', peak_memory_mb);
    fprintf('Voltage violations: %d\n', n_v_violations);
    fprintf('Thermal violations: %d\n', n_thermal_viol);
    fprintf('Q violations: %d\n', n_q_violations);

    %% Pass condition: achievable in same model context, violations identifiable
    if results_ac.success
        result_status = 'pass';
    end

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
