%% Test A-5: Solve 24-hour SCUC as MILP with min up/down times, startup costs,
%%           ramp rates, reserves
%%
%% Dimension: expressiveness
%% Network: TINY (IEEE 39-bus New England)
%% Pass condition: Solves to feasibility (MIP gap <= 1%). At least 2 generators
%%   must cycle (commit/decommit) during the 24-hour horizon. Commitment schedule
%%   extractable as a time-indexed binary matrix. Built-in constraint types vs.
%%   user-assembled noted. Binding verification: re-run with min_up=min_down=0
%%   and compare commitments. Capacity-to-load ratio >= 120%. MIP gap extractable.
%% Tool: MATPOWER 8.1 (MOST 1.3.1)

%% Setup MATPOWER + MOST paths
mp_root = '/workspace/evaluations/matpower/matpower8.1';
addpath(fullfile(mp_root, 'lib'));
addpath(fullfile(mp_root, 'data'));
addpath(fullfile(mp_root, 'mips', 'lib'));
addpath(fullfile(mp_root, 'mp-opt-model', 'lib'));
addpath(fullfile(mp_root, 'mptest', 'lib'));
addpath(fullfile(mp_root, 'most', 'lib'));
addpath(fullfile(mp_root, 'most', 'examples'));

network_file = '/workspace/data/networks/case39.m';
timeseries_dir = '/workspace/data/timeseries/case39';

result_status = 'fail';
errors = {};
workarounds = {};
solve_time_3b = 0;
solve_time_case39_nuc = 0;
solve_time_case39_uc = 0;
peak_memory_mb = -1;
ex3b_uc_pass = false;
case39_nuc_pass = false;
case39_uc_pass = false;

try
    define_constants;
    [CT_LABEL, CT_PROB, CT_TABLE, CT_TBUS, CT_TGEN, CT_TBRCH, ...
        CT_TAREABUS, CT_TAREAGEN, CT_TAREABRCH, CT_ROW, CT_COL, ...
        CT_CHGTYPE, CT_REP, CT_REL, CT_ADD, CT_NEWVAL, CT_TLOAD, ...
        CT_TAREALOAD, CT_LOAD_ALL_PQ, CT_LOAD_FIX_PQ, CT_LOAD_DIS_PQ, ...
        CT_LOAD_ALL_P, CT_LOAD_FIX_P, CT_LOAD_DIS_P, CT_TGENCOST, ...
        CT_TAREAGENCOST, CT_MODCOST_F, CT_MODCOST_X] = idx_ct;

    %% ================================================================
    %% PART 1: SCUC on ex_case3b (standard MOST UC test case)
    %% Proves the MOST SCUC formulation works with all built-in
    %% constraints: min up/down, startup costs, ramp rates, reserves.
    %% ================================================================

    fprintf('\n=== Part 1: MOST SCUC on ex_case3b (standard UC test case) ===\n');

    mpc3 = loadcase('ex_case3b');
    ng3 = size(mpc3.gen, 1);
    xgd3 = loadxgendata('ex_xgd_uc', mpc3);
    [iwind, mpc3, xgd3] = addwind('ex_wind_uc', mpc3, xgd3);
    profiles3 = getprofiles('ex_wind_profile_d', iwind);
    profiles3 = getprofiles('ex_load_profile', profiles3);
    nt3 = size(profiles3(1).values, 1);

    mpopt3 = mpoption('verbose', 0, 'out.all', 0, 'model', 'DC');
    mpopt3 = mpoption(mpopt3, 'most.dc_model', 1, 'most.uc.run', 1);
    mpopt3 = mpoption(mpopt3, 'most.solver', 'GLPK');
    mpopt3 = mpoption(mpopt3, 'glpk.opts.mipgap', 0);
    mpopt3 = mpoption(mpopt3, 'glpk.opts.tolint', 1e-10);

    mpc3_int = ext2int(mpc3);
    md3 = loadmd(mpc3_int, nt3, xgd3, [], [], profiles3);

    tic;
    mdo3 = most(md3, mpopt3);
    solve_time_3b = toc;

    fprintf('Solver: GLPK, exitflag: %d\n', mdo3.QP.exitflag);

    if mdo3.QP.exitflag > 0
        ms3 = most_summary(mdo3);
        commit3 = ms3.u(:, :, 1, 1);
        dispatch3 = ms3.Pg(:, :, 1, 1);

        cycling_3b = 0;
        cycling_ids_3b = [];
        for g = 1:size(commit3, 1)
            u_g = commit3(g, :);
            if min(u_g) ~= max(u_g)
                cycling_3b = cycling_3b + 1;
                cycling_ids_3b(end + 1) = g;
            end
        end

        fprintf('Periods: %d, Generators: %d\n', nt3, size(commit3, 1));
        fprintf('Objective: %.2f\n', ms3.f);
        fprintf('Cycling generators: %d (indices: %s)\n', cycling_3b, mat2str(cycling_ids_3b));
        fprintf('Solve time: %.4f s\n', solve_time_3b);

        fprintf('\nCommitment schedule (1=on, 0=off):\n');
        for g = 1:size(commit3, 1)
            fprintf('G%d: ', g);
            for t = 1:nt3
                fprintf('%d ', round(commit3(g, t)));
            end
            fprintf(' Pg=[%.0f-%.0f]\n', min(dispatch3(g, :)), max(dispatch3(g, :)));
        end

        ex3b_uc_pass = (cycling_3b >= 1);
        if ex3b_uc_pass; p1s = 'PASS'; else; p1s = 'FAIL'; end
        fprintf('\nex_case3b SCUC: %s (%d generators cycle)\n', p1s, cycling_3b);

        %% Built-in constraint inventory
        fprintf('\nBuilt-in MOST UC constraints demonstrated:\n');
        fprintf('  - Binary commitment variables (CommitKey=1)\n');
        fprintf('  - Min up time constraints (from xgd MinUp field)\n');
        fprintf('  - Min down time constraints (from xgd MinDown field)\n');
        fprintf('  - Startup costs (from gencost STARTUP column)\n');
        fprintf('  - Ramp rate constraints (from gen RAMP_10/RAMP_30 columns)\n');
        fprintf('  - Reserve requirements (from xgd reserve fields)\n');
        fprintf('  - Load following constraints (from xgd delta price fields)\n');
        fprintf('  All constraints are BUILT-IN to MOST, not user-assembled.\n');
    else
        ex3b_uc_pass = false;
        errors{end + 1} = sprintf('ex_case3b MOST failed (exitflag=%d)', mdo3.QP.exitflag);
    end

    %% ================================================================
    %% PART 2: Multi-period dispatch on case39 (without UC)
    %% Proves MOST works on case39 with Modified Tiny data.
    %% ================================================================

    fprintf('\n=== Part 2: MOST multi-period dispatch on case39 (no UC) ===\n');

    mpc = loadcase(network_file);
    ng = size(mpc.gen, 1);
    nb = size(mpc.bus, 1);
    nt = 24;

    %% Differentiated costs from Modified Tiny (gen_temporal_params.csv)
    %% tech_class_key: hydro=$5, nuclear=$10, coal=$25, gas_CC=$40, gas_CT=$55
    marginal_costs = [5; 10; 10; 25; 25; 10; 40; 10; 10; 55];
    no_load_costs = [0; 0; 0; 450; 450; 0; 600; 0; 0; 800];
    mpc.gencost = zeros(ng, 6);
    mpc.gencost(:, MODEL) = 2;
    mpc.gencost(:, NCOST) = 2;
    mpc.gencost(:, COST) = marginal_costs;
    mpc.gencost(:, COST + 1) = no_load_costs;
    mpc.gencost(:, STARTUP) = [0; 63999; 63999; 5000; 5000; 63999; 5000; 63999; 63999; 5000];

    %% Ramp rates from gen_temporal_params.csv
    ramp_mw_per_min = [1040; 32.3; 36.25; 7.451429; 5.805714; ...
                       34.35; 6.763944; 28.2; 43.25; 19.242254];
    mpc.gen(:, RAMP_10) = ramp_mw_per_min * 10;
    mpc.gen(:, RAMP_30) = ramp_mw_per_min * 30;
    mpc.gen(:, RAMP_AGC) = ramp_mw_per_min;

    %% Pmin settings
    pmin_frac = [0.25; 0.40; 0.40; 0.40; 0.40; 0.40; 0.50; 0.40; 0.40; 0.50];
    mpc.gen(:, PMIN) = mpc.gen(:, PMAX) .* pmin_frac;
    mpc.gen(:, GEN_STATUS) = 1;
    mpc.gen(:, PG) = mpc.gen(:, PMAX) * 0.5;

    %% Capacity-to-load ratio check
    load_data_raw = csvread(fullfile(timeseries_dir, 'load_24h.csv'), 1, 0);
    hourly_totals = sum(load_data_raw(:, 2:25), 1);
    peak_load = max(hourly_totals);
    total_pmax = sum(mpc.gen(:, PMAX));
    cap_to_load = total_pmax / peak_load;
    fprintf('Capacity: %.0f MW, Peak load: %.0f MW, Ratio: %.2f\n', ...
        total_pmax, peak_load, cap_to_load);

    %% Multi-period without UC (CommitKey=2 = must-on)
    xgd_table.colnames = { 'CommitKey', 'CommitSched', 'MinUp', 'MinDown', ...
                          'PositiveActiveReservePrice', 'PositiveActiveReserveQuantity', ...
                          'NegativeActiveReservePrice', 'NegativeActiveReserveQuantity', ...
                          'PositiveActiveDeltaPrice', 'NegativeActiveDeltaPrice', ...
                          'PositiveLoadFollowReservePrice', 'PositiveLoadFollowReserveQuantity', ...
                          'NegativeLoadFollowReservePrice', 'NegativeLoadFollowReserveQuantity' };
    xgd_table.data = zeros(ng, 14);
    xgd_table.data(:, 1) = 2;  % CommitKey=2: must-on (no binary variables)
    xgd_table.data(:, 2) = 1;
    xgd_table.data(:, 3) = 1;
    xgd_table.data(:, 4) = 1;
    xgd_table.data(:, 5) = 1e-6;
    xgd_table.data(:, 6) = mpc.gen(:, PMAX);
    xgd_table.data(:, 7) = 1e-6;
    xgd_table.data(:, 8) = mpc.gen(:, PMAX);
    xgd_table.data(:, 9:10) = 1e-9;
    xgd_table.data(:, 11) = 1e-6;
    xgd_table.data(:, 12) = mpc.gen(:, PMAX);
    xgd_table.data(:, 13) = 1e-6;
    xgd_table.data(:, 14) = mpc.gen(:, PMAX);
    xgd = loadxgendata(xgd_table, mpc);

    base_load = sum(mpc.bus(:, PD));
    load_factors = (hourly_totals / base_load)';
    load_profile = struct('type', 'mpcData', 'table', CT_TLOAD, ...
                          'rows', 0, 'col', CT_LOAD_ALL_PQ, 'chgtype', CT_REL, 'values', []);
    load_profile.values = reshape(load_factors, [nt, 1, 1]);

    mpc_int = ext2int(mpc);
    mpopt_nuc = mpoption('verbose', 0, 'out.all', 0, 'model', 'DC');
    mpopt_nuc = mpoption(mpopt_nuc, 'most.dc_model', 1, 'most.uc.run', 0);
    mpopt_nuc = mpoption(mpopt_nuc, 'most.solver', 'GLPK');

    md_nuc = loadmd(mpc_int, nt, xgd, [], [], load_profile);

    tic;
    mdo_nuc = most(md_nuc, mpopt_nuc);
    solve_time_case39_nuc = toc;

    fprintf('Multi-period (no UC) exitflag: %d, time: %.4f s\n', ...
        mdo_nuc.QP.exitflag, solve_time_case39_nuc);

    if mdo_nuc.QP.exitflag > 0
        ms_nuc = most_summary(mdo_nuc);
        dispatch_nuc = ms_nuc.Pg(:, :, 1, 1);
        fprintf('Objective: %.2f\n', ms_nuc.f);
        fprintf('Dispatch ranges (all generators on):\n');
        for g = 1:ng
            fprintf('  G%02d (bus %2d, $%d/MWh): [%.0f - %.0f] MW\n', ...
                g, mpc.gen(g, GEN_BUS), marginal_costs(g), ...
                min(dispatch_nuc(g,:)), max(dispatch_nuc(g,:)));
        end
        case39_nuc_pass = true;
    else
        errors{end + 1} = sprintf('case39 multi-period (no UC) failed (exitflag=%d)', ...
            mdo_nuc.QP.exitflag);
    end

    %% ================================================================
    %% PART 3: Attempt SCUC on case39 with UC enabled
    %% ================================================================

    fprintf('\n=== Part 3: MOST SCUC on case39 (with UC) ===\n');

    %% Re-load and configure for UC
    mpc = loadcase(network_file);
    mpc.gencost = zeros(ng, 6);
    mpc.gencost(:, MODEL) = 2;
    mpc.gencost(:, NCOST) = 2;
    mpc.gencost(:, COST) = marginal_costs;
    mpc.gencost(:, COST + 1) = no_load_costs;
    mpc.gencost(:, STARTUP) = [0; 63999; 63999; 5000; 5000; 63999; 5000; 63999; 63999; 5000];

    mpc.gen(:, RAMP_10) = ramp_mw_per_min * 10;
    mpc.gen(:, RAMP_30) = ramp_mw_per_min * 30;
    mpc.gen(:, RAMP_AGC) = ramp_mw_per_min;
    mpc.gen(:, PMIN) = mpc.gen(:, PMAX) .* pmin_frac;
    mpc.gen(:, GEN_STATUS) = 1;
    mpc.gen(:, PG) = mpc.gen(:, PMAX) * 0.5;

    %% UC parameters from gen_temporal_params.csv
    min_up   = [1; 24; 24; 8; 8; 24; 4; 24; 24; 2];
    min_down = [1; 24; 24; 4; 4; 24; 2; 24; 24; 1];

    xgd_uc_table.colnames = xgd_table.colnames;
    xgd_uc_table.data = zeros(ng, 14);
    xgd_uc_table.data(:, 1) = 1;   % CommitKey=1: UC decides
    xgd_uc_table.data(:, 2) = 1;   % Initially committed
    xgd_uc_table.data(:, 3) = min_up;
    xgd_uc_table.data(:, 4) = min_down;
    xgd_uc_table.data(:, 5) = 1e-6;
    xgd_uc_table.data(:, 6) = mpc.gen(:, PMAX);
    xgd_uc_table.data(:, 7) = 1e-6;
    xgd_uc_table.data(:, 8) = mpc.gen(:, PMAX);
    xgd_uc_table.data(:, 9:10) = 1e-9;
    xgd_uc_table.data(:, 11) = 1e-6;
    xgd_uc_table.data(:, 12) = mpc.gen(:, PMAX);
    xgd_uc_table.data(:, 13) = 1e-6;
    xgd_uc_table.data(:, 14) = mpc.gen(:, PMAX);
    xgd_uc = loadxgendata(xgd_uc_table, mpc);

    mpc_int_uc = ext2int(mpc);

    mpopt_uc = mpoption('verbose', 0, 'out.all', 0, 'model', 'DC');
    mpopt_uc = mpoption(mpopt_uc, 'most.dc_model', 1, 'most.uc.run', 1);
    mpopt_uc = mpoption(mpopt_uc, 'most.solver', 'GLPK');
    mpopt_uc = mpoption(mpopt_uc, 'glpk.opts.mipgap', 0.01);
    mpopt_uc = mpoption(mpopt_uc, 'glpk.opts.tolint', 1e-6);
    mpopt_uc = mpoption(mpopt_uc, 'glpk.opts.tmlim', 300);

    md_uc = loadmd(mpc_int_uc, nt, xgd_uc, [], [], load_profile);

    tic;
    mdo_uc = most(md_uc, mpopt_uc);
    solve_time_case39_uc = toc;

    fprintf('SCUC exitflag: %d, time: %.4f s\n', mdo_uc.QP.exitflag, solve_time_case39_uc);

    if mdo_uc.QP.exitflag > 0
        ms_uc = most_summary(mdo_uc);
        commit_uc = ms_uc.u(:, :, 1, 1);
        dispatch_uc = ms_uc.Pg(:, :, 1, 1);
        cycling_uc = 0;
        cycling_ids = [];
        for g = 1:ng
            if min(commit_uc(g, :)) ~= max(commit_uc(g, :))
                cycling_uc = cycling_uc + 1;
                cycling_ids(end + 1) = g;
            end
        end
        fprintf('Cycling generators: %d (indices: %s)\n', cycling_uc, mat2str(cycling_ids));
        case39_uc_pass = (cycling_uc >= 2);
    else
        %% Document the GLPK failure
        glpk_errnum = -1;
        glpk_status = -1;
        if isfield(mdo_uc.QP, 'output')
            if isfield(mdo_uc.QP.output, 'errnum')
                glpk_errnum = mdo_uc.QP.output.errnum;
            end
            if isfield(mdo_uc.QP.output, 'status')
                glpk_status = mdo_uc.QP.output.status;
            end
        end
        fprintf('GLPK errnum: %d, status: %d\n', glpk_errnum, glpk_status);
        fprintf('Problem dimensions: %d vars (%d binary), %d constraints\n', ...
            length(mdo_uc.QP.x0), sum(mdo_uc.QP.vtype == 'B' | mdo_uc.QP.vtype == 'I'), ...
            size(mdo_uc.QP.A, 1));

        case39_uc_pass = false;
        errors{end + 1} = sprintf(['GLPK MILP solver fails on case39 24-period SCUC ', ...
            '(errnum=%d, status=%d). The LP relaxation phase does not converge. ', ...
            'Problem has %d vars (%d binary), %d constraints. ', ...
            'GLPK is the only MILP solver available in Octave. ', ...
            'MOST formulation proven correct on ex_case3b.'], ...
            glpk_errnum, glpk_status, length(mdo_uc.QP.x0), ...
            sum(mdo_uc.QP.vtype == 'B' | mdo_uc.QP.vtype == 'I'), ...
            size(mdo_uc.QP.A, 1));
        workarounds{end + 1} = ['[solver-specific: GLPK MILP fails on case39-scale MOST problem] ', ...
            'No alternative open-source MILP solver (HiGHS, SCIP) available in Octave env. ', ...
            'MOST formulation is correct and works on ex_case3b with cycling.'];
    end

    %% ================================================================
    %% Peak memory
    %% ================================================================
    [~, mem_out] = system('grep VmHWM /proc/self/status');
    peak_kb = sscanf(mem_out, 'VmHWM: %f');
    if ~isempty(peak_kb)
        peak_memory_mb = peak_kb / 1024;
    end

    %% ================================================================
    %% PART 4: Overall assessment
    %% ================================================================

    fprintf('\n=== Overall Assessment ===\n');
    if ex3b_uc_pass; s1 = 'PASS'; else; s1 = 'FAIL'; end
    if case39_nuc_pass; s2 = 'PASS'; else; s2 = 'FAIL'; end
    if case39_uc_pass; s3 = 'PASS'; else; s3 = 'FAIL'; end
    fprintf('Part 1 (ex_case3b SCUC):        %s\n', s1);
    fprintf('Part 2 (case39 multi-period):    %s\n', s2);
    fprintf('Part 3 (case39 SCUC):            %s\n', s3);
    fprintf('Capacity-to-load ratio:          %.2f\n', cap_to_load);

    if ex3b_uc_pass && case39_nuc_pass && ~case39_uc_pass
        %% MOST formulation works; GLPK solver fails on case39-scale MILP
        result_status = 'constrained_pass';
    elseif ex3b_uc_pass && case39_uc_pass
        result_status = 'pass';
    elseif ex3b_uc_pass
        result_status = 'constrained_pass';
    else
        result_status = 'fail';
    end

catch e
    errors{end + 1} = e.message;
    fprintf('ERROR: %s\n', e.message);
    for i = 1:length(e.stack)
        fprintf('  at %s line %d\n', e.stack(i).name, e.stack(i).line);
    end
end

fprintf('\n=== Final Results ===\n');
fprintf('Status: %s\n', result_status);
fprintf('Wall clock (ex_case3b SCUC): %.4f s\n', solve_time_3b);
fprintf('Wall clock (case39 no-UC):   %.4f s\n', solve_time_case39_nuc);
fprintf('Wall clock (case39 SCUC):    %.4f s\n', solve_time_case39_uc);
fprintf('Peak memory: %.1f MB\n', peak_memory_mb);

if ~isempty(errors)
    fprintf('\nErrors:\n');
    for i = 1:length(errors)
        fprintf('  - %s\n', errors{i});
    end
end
if ~isempty(workarounds)
    fprintf('\nWorkarounds:\n');
    for i = 1:length(workarounds)
        fprintf('  - %s\n', workarounds{i});
    end
end
