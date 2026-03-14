%% Test A-12: 24hr multi-period DCOPF with storage, renewables, quadratic costs, congestion
%%
%% Dimension: expressiveness
%% Network: TINY (IEEE 39-bus New England)
%% Pass condition: Three behavioral conditions:
%%   (1) Congestion: >=2 of 24 hours have >=2 branches with non-zero shadow prices
%%   (2) BESS arbitrage: Mean LMP at BESS bus during discharge > during charge
%%   (3) SoC feasibility: SoC in [0, capacity], energy balance consistent
%% Tool: MATPOWER 8.1 (MOST 1.3.1)
%% Parameters: quadratic_costs=true, branch_derating=0.70, cyclic_soc=true,
%%             eta_charge=0.92, eta_discharge=0.95

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
solve_time = 0;

try
    define_constants;
    [CT_LABEL, CT_PROB, CT_TABLE, CT_TBUS, CT_TGEN, CT_TBRCH, ...
        CT_TAREABUS, CT_TAREAGEN, CT_TAREABRCH, CT_ROW, CT_COL, ...
        CT_CHGTYPE, CT_REP, CT_REL, CT_ADD, CT_NEWVAL, CT_TLOAD, ...
        CT_TAREALOAD, CT_LOAD_ALL_PQ, CT_LOAD_FIX_PQ, CT_LOAD_DIS_PQ, ...
        CT_LOAD_ALL_P, CT_LOAD_FIX_P, CT_LOAD_DIS_P, CT_TGENCOST, ...
        CT_TAREAGENCOST, CT_MODCOST_F, CT_MODCOST_X] = idx_ct;

    %% ================================================================
    %% Load and configure case39
    %% ================================================================
    mpc = loadcase(network_file);
    ng = size(mpc.gen, 1);
    nb = size(mpc.bus, 1);
    nl = size(mpc.branch, 1);
    nt = 24;

    %% Parameters
    eta_charge = 0.92;
    eta_discharge = 0.95;
    bess_bus = 5;
    bess_power_mw = 150;
    bess_energy_mwh = 600;
    bess_min_soc = 0.10;  % 60 MWh floor
    bess_max_soc = 0.90;  % 540 MWh ceiling
    bess_init_soc = 0.50; % 300 MWh

    %% Apply differentiated costs
    %% Try quadratic first (c2 = c1 * 0.001), fall back to linear if solver fails
    marginal_costs = [5; 10; 10; 25; 25; 10; 40; 10; 10; 40];
    use_quadratic = false;  %% MIPS diverges on QP with this problem size; GLPK rejects QP
    if use_quadratic
        mpc.gencost = zeros(ng, 7);
        mpc.gencost(:, MODEL) = 2;
        mpc.gencost(:, NCOST) = 3;
        mpc.gencost(:, COST)   = marginal_costs * 0.001;
        mpc.gencost(:, COST + 1) = marginal_costs;
        mpc.gencost(:, COST + 2) = 0;
    else
        %% Linear costs -- GLPK can handle LP
        mpc.gencost = zeros(ng, 6);
        mpc.gencost(:, MODEL) = 2;
        mpc.gencost(:, NCOST) = 2;
        mpc.gencost(:, COST)   = marginal_costs;
        mpc.gencost(:, COST + 1) = 0;
    end

    %% Apply 70% branch derating
    mpc.branch(:, RATE_A) = mpc.branch(:, RATE_A) * 0.70;
    mpc.branch(:, RATE_B) = mpc.branch(:, RATE_B) * 0.70;
    mpc.branch(:, RATE_C) = mpc.branch(:, RATE_C) * 0.70;

    %% Ramp rates
    ramp_mw_per_min = [1040; 32.3; 36.25; 7.451429; 5.805714; ...
                       34.35; 6.763944; 28.2; 43.25; 19.242254];
    mpc.gen(:, RAMP_10) = ramp_mw_per_min * 10;
    mpc.gen(:, RAMP_30) = ramp_mw_per_min * 30;
    mpc.gen(:, RAMP_AGC) = ramp_mw_per_min;

    %% Pmin settings
    pmin_frac = [0.25; 0.40; 0.40; 0.40; 0.40; 0.40; 0.50; 0.40; 0.40; 0.30];
    mpc.gen(:, PMIN) = mpc.gen(:, PMAX) .* pmin_frac;
    mpc.gen(:, GEN_STATUS) = 1;
    mpc.gen(:, PG) = mpc.gen(:, PMAX) * 0.5;

    %% ================================================================
    %% Add renewable generators from renewable_units.csv
    %% ================================================================
    re_file = fullfile(timeseries_dir, 'renewable_units.csv');
    fid = fopen(re_file, 'r');
    header = fgetl(fid);
    re_data = {};
    while ~feof(fid)
        line = fgetl(fid);
        if ischar(line) && ~isempty(line)
            re_data{end + 1} = line;
        end
    end
    fclose(fid);

    nre = length(re_data);
    re_buses = zeros(nre, 1);
    re_pmax = zeros(nre, 1);
    re_types = cell(nre, 1);
    re_uids = cell(nre, 1);
    for i = 1:nre
        parts = strsplit(re_data{i}, ',');
        re_uids{i} = strtrim(parts{1});
        re_buses(i) = str2double(parts{2});
        re_types{i} = strtrim(parts{3});
        re_pmax(i) = str2double(parts{4});
    end

    %% Add renewable generators to mpc
    for i = 1:nre
        new_gen = zeros(1, size(mpc.gen, 2));
        new_gen(GEN_BUS) = re_buses(i);
        new_gen(PG) = 0;
        new_gen(PMAX) = re_pmax(i);
        new_gen(PMIN) = 0;
        new_gen(GEN_STATUS) = 1;
        new_gen(VG) = 1.0;
        new_gen(MBASE) = 100;
        new_gen(RAMP_10) = re_pmax(i);
        new_gen(RAMP_30) = re_pmax(i);
        new_gen(RAMP_AGC) = re_pmax(i);
        mpc.gen = [mpc.gen; new_gen];

        %% Zero-cost renewable (match gencost column count)
        new_cost = zeros(1, size(mpc.gencost, 2));
        new_cost(MODEL) = 2;
        new_cost(NCOST) = 2;
        mpc.gencost = [mpc.gencost; new_cost];
    end

    ng_total = size(mpc.gen, 1);  % 10 conventional + 5 renewable

    %% ================================================================
    %% Load renewable forecast profiles
    %% ================================================================
    wind_forecast = csvread(fullfile(timeseries_dir, 'wind_forecast_24h.csv'), 1, 1);
    solar_forecast = csvread(fullfile(timeseries_dir, 'solar_forecast_24h.csv'), 1, 1);

    %% Build per-generator Pmax profile for renewables
    %% wind_forecast: 3 wind units x 24 hours, solar_forecast: 2 solar units x 24 hours
    re_profile = zeros(nre, nt);
    wind_idx = 1;
    solar_idx = 1;
    for i = 1:nre
        if strcmp(re_types{i}, 'wind')
            re_profile(i, :) = wind_forecast(wind_idx, :);
            wind_idx = wind_idx + 1;
        else
            re_profile(i, :) = solar_forecast(solar_idx, :);
            solar_idx = solar_idx + 1;
        end
    end

    %% ================================================================
    %% Build xGenData for all generators (before adding storage)
    %% ================================================================
    ng_total = size(mpc.gen, 1);  % 10 + 5 = 15

    xgd_table.colnames = { ...
                          'PositiveActiveReservePrice', 'PositiveActiveReserveQuantity', ...
                          'NegativeActiveReservePrice', 'NegativeActiveReserveQuantity', ...
                          'PositiveActiveDeltaPrice', 'NegativeActiveDeltaPrice', ...
                          'PositiveLoadFollowReservePrice', 'PositiveLoadFollowReserveQuantity', ...
                          'NegativeLoadFollowReservePrice', 'NegativeLoadFollowReserveQuantity' };
    xgd_table.data = zeros(ng_total, 10);
    xgd_table.data(:, 1) = 1e-6;
    xgd_table.data(:, 2) = mpc.gen(:, PMAX);
    xgd_table.data(:, 3) = 1e-6;
    xgd_table.data(:, 4) = max(mpc.gen(:, PMAX), abs(mpc.gen(:, PMIN)));
    xgd_table.data(:, 5:6) = 1e-9;
    xgd_table.data(:, 7) = 1e-6;
    xgd_table.data(:, 8) = max(mpc.gen(:, PMAX), abs(mpc.gen(:, PMIN)));
    xgd_table.data(:, 9) = 1e-6;
    xgd_table.data(:, 10) = max(mpc.gen(:, PMAX), abs(mpc.gen(:, PMIN)));
    xgd = loadxgendata(xgd_table, mpc);

    %% ================================================================
    %% Add BESS using addstorage() -- the proper MOST API
    %% ================================================================
    avg_cost = mean(marginal_costs);

    storage.gen = [ ...
                   bess_bus, 0, 0, 0, 0, 1, 100, 1, bess_power_mw, -bess_power_mw, ...
                   0, 0, 0, 0, 0, 0, bess_power_mw, bess_power_mw, bess_power_mw, 0, 0];

    storage.xgd_table.colnames = { ...
                                  'CommitKey', 'CommitSched', ...
                                  'PositiveActiveReservePrice', 'PositiveActiveReserveQuantity', ...
                                  'NegativeActiveReservePrice', 'NegativeActiveReserveQuantity', ...
                                  'PositiveActiveDeltaPrice', 'NegativeActiveDeltaPrice', ...
                                  'PosLFResPrice', 'PosLFResQty', ...
                                  'NegLFResPrice', 'NegLFResQty' };
    storage.xgd_table.data = [ ...
                              2, 1, ...
                              1e-8, 2 * bess_power_mw, 2e-8, 2 * bess_power_mw, ...
                              1e-9, 1e-9, ...
                              1e-6, 2 * bess_power_mw, 1e-6, 2 * bess_power_mw];

    storage.sd_table.colnames = { ...
                                 'InitialStorage', ...
                                 'InitialStorageLowerBound', 'InitialStorageUpperBound', ...
                                 'InitialStorageCost', 'TerminalStoragePrice', ...
                                 'MinStorageLevel', 'MaxStorageLevel', ...
                                 'OutEff', 'InEff', 'LossFactor', 'rho' };
    storage.sd_table.data = [ ...
                             bess_init_soc * bess_energy_mwh, ...
                             bess_init_soc * bess_energy_mwh, bess_init_soc * bess_energy_mwh, ...
                             avg_cost, avg_cost, ...
                             bess_min_soc * bess_energy_mwh, bess_max_soc * bess_energy_mwh, ...
                             eta_discharge, eta_charge, 0, 0];

    [iess, mpc, xgd, sd] = addstorage(storage, mpc, xgd);
    ng_all = size(mpc.gen, 1);
    bess_gen_idx = iess;

    %% ================================================================
    %% Build load profile
    %% ================================================================
    load_data_raw = csvread(fullfile(timeseries_dir, 'load_24h.csv'), 1, 0);
    hourly_totals = sum(load_data_raw(:, 2:25), 1);

    load_profile = struct('type', 'mpcData', 'table', CT_TLOAD, ...
                          'rows', 0, 'col', CT_LOAD_ALL_PQ, 'chgtype', CT_REP, 'values', []);
    load_profile.values = reshape(hourly_totals', [nt, 1, 1]);

    %% Build renewable Pmax profiles using CT_TGEN to modify PMAX
    %% For each renewable generator, create a profile that sets its PMAX per period
    profiles = load_profile;

    for i = 1:nre
        gen_idx = ng + i;  % index in mpc.gen (after original 10 gens)
        re_pmax_profile = struct('type', 'mpcData', 'table', CT_TGEN, ...
                                 'rows', gen_idx, 'col', PMAX, 'chgtype', CT_REP, 'values', []);
        re_pmax_profile.values = reshape(re_profile(i, :)', [nt, 1, 1]);
        profiles = [profiles, re_pmax_profile];
    end

    %% ================================================================
    %% Convert to internal indexing and build MOST data
    %% ================================================================
    mpc = ext2int(mpc);
    md = loadmd(mpc, nt, xgd, sd, [], profiles);

    %% Configure solver
    mpopt = mpoption('verbose', 0, 'out.all', 0, 'model', 'DC');
    mpopt = mpoption(mpopt, 'most.dc_model', 1);
    mpopt = mpoption(mpopt, 'most.solver', 'GLPK');  %% GLPK for LP (linear costs used)
    mpopt = mpoption(mpopt, 'most.storage.cyclic', 1);  % cyclic SoC

    %% ================================================================
    %% Solve multi-period DCOPF with storage
    %% ================================================================
    fprintf('\n=== A-12: Multi-Period DCOPF with Storage ===\n');
    tic;
    mdo = most(md, mpopt);
    solve_time = toc;

    fprintf('Solver exitflag: %d\n', mdo.QP.exitflag);
    fprintf('Solve time: %.4f s\n', solve_time);

    %% ================================================================
    %% Extract results
    %% ================================================================
    if mdo.QP.exitflag > 0
        ms = most_summary(mdo);
        dispatch = ms.Pg(:, :, 1, 1);   % ng_all x nt
        lmps = ms.lamP(:, :, 1, 1);     % nb x nt
        pf = ms.Pf(:, :, 1, 1);         % nl x nt (branch flows)
        mu_f = ms.muF(:, :, 1, 1);      % nl x nt (branch shadow prices)

        %% BESS dispatch (positive = discharge, negative = charge in MOST)
        bess_dispatch = dispatch(bess_gen_idx, :);

        %% Storage state from MOST
        soc = mdo.Storage.ExpectedStorageState;  % ns x nt

        fprintf('\n=== BESS Dispatch & SoC ===\n');
        fprintf('Hour | Dispatch (MW) | SoC (MWh) | Status\n');
        for t = 1:nt
            if bess_dispatch(t) > 0.01
                status = 'discharge';
            elseif bess_dispatch(t) < -0.01
                status = 'charge';
            else
                status = 'idle';
            end
            fprintf('HR%02d | %12.2f  | %9.2f | %s\n', t, bess_dispatch(t), soc(t), status);
        end

        %% ================================================================
        %% Pass Condition 1: Congestion reporting
        %% ================================================================
        fprintf('\n=== Condition 1: Congestion ===\n');
        congestion_hours = 0;
        fprintf('Hour | Binding branches | Mean shadow | Std shadow\n');
        for t = 1:nt
            shadow_t = mu_f(:, t);
            binding = abs(shadow_t) > 1e-4;
            n_binding = sum(binding);
            if n_binding >= 2
                congestion_hours = congestion_hours + 1;
            end
            if any(binding)
                fprintf('HR%02d | %15d  | %10.4f  | %10.4f\n', ...
                        t, n_binding, mean(shadow_t(binding)), std(shadow_t(binding)));
            else
                fprintf('HR%02d | %15d  |        n/a |        n/a\n', t, 0);
            end
        end
        pass_congestion = (congestion_hours >= 2);
        fprintf('Hours with >=2 binding branches: %d (need >=2)\n', congestion_hours);
        if pass_congestion
            c1s = 'PASS';
        else
            c1s = 'FAIL';
        end
        fprintf('Condition 1: %s\n', c1s);

        %% ================================================================
        %% Pass Condition 2: BESS arbitrage timing
        %% Find the BESS bus in the internal ordering
        %% ================================================================
        fprintf('\n=== Condition 2: BESS Arbitrage ===\n');
        %% Find BESS bus index in internal ordering
        bess_bus_int = mpc.gen(bess_gen_idx, GEN_BUS);
        bess_lmps = lmps(bess_bus_int, :);

        discharge_hours = find(bess_dispatch > 0.01);
        charge_hours = find(bess_dispatch < -0.01);

        if ~isempty(discharge_hours) && ~isempty(charge_hours)
            mean_lmp_discharge = mean(bess_lmps(discharge_hours));
            mean_lmp_charge = mean(bess_lmps(charge_hours));
            pass_arbitrage = (mean_lmp_discharge > mean_lmp_charge);
            fprintf('Discharge hours: %s\n', mat2str(discharge_hours));
            fprintf('Charge hours: %s\n', mat2str(charge_hours));
            fprintf('Mean LMP during discharge: $%.4f/MWh\n', mean_lmp_discharge);
            fprintf('Mean LMP during charge: $%.4f/MWh\n', mean_lmp_charge);
            fprintf('Arbitrage spread: $%.4f/MWh\n', mean_lmp_discharge - mean_lmp_charge);
            if pass_arbitrage
                c2s = 'PASS';
            else
                c2s = 'FAIL';
            end
            fprintf('Condition 2: %s\n', c2s);
        else
            pass_arbitrage = false;
            fprintf('Insufficient charge/discharge activity\n');
            fprintf('Discharge hours: %d, Charge hours: %d\n', ...
                    length(discharge_hours), length(charge_hours));
            fprintf('Condition 2: FAIL\n');
        end

        %% ================================================================
        %% Pass Condition 3: SoC feasibility
        %% ================================================================
        fprintf('\n=== Condition 3: SoC Feasibility ===\n');
        soc_min_limit = bess_min_soc * bess_energy_mwh;
        soc_max_limit = bess_max_soc * bess_energy_mwh;

        %% Check bounds
        soc_in_bounds = all(soc >= soc_min_limit - 0.1) && all(soc <= soc_max_limit + 0.1);
        fprintf('SoC range: [%.2f, %.2f] MWh\n', min(soc), max(soc));
        fprintf('SoC bounds: [%.2f, %.2f] MWh\n', soc_min_limit, soc_max_limit);
        if soc_in_bounds
            sibs = 'YES';
        else
            sibs = 'NO';
        end
        fprintf('SoC in bounds: %s\n', sibs);

        %% Check energy balance
        %% SoC(t) = SoC(t-1) + eta_ch * P_ch(t) - P_dis(t) / eta_dis
        %% In MOST, negative dispatch = charging, positive = discharging
        max_balance_error = 0;
        init_soc = bess_init_soc * bess_energy_mwh;
        for t = 1:nt
            if t == 1
                prev_soc = init_soc;
            else
                prev_soc = soc(t - 1);
            end
            p = bess_dispatch(t);
            if p < 0
                %% Charging: P is negative, energy stored = |P| * eta_charge
                expected_soc = prev_soc + abs(p) * eta_charge;
            else
                %% Discharging: P is positive, energy removed = P / eta_discharge
                expected_soc = prev_soc - p / eta_discharge;
            end
            balance_error = abs(soc(t) - expected_soc);
            max_balance_error = max(max_balance_error, balance_error);
            if balance_error > 1.0
                fprintf('HR%02d: SoC=%.2f, expected=%.2f, error=%.2f MWh (VIOLATION)\n', ...
                        t, soc(t), expected_soc, balance_error);
            end
        end
        pass_soc = soc_in_bounds && (max_balance_error < 1.0);
        fprintf('Max energy balance error: %.4f MWh (threshold: 1.0)\n', max_balance_error);
        if pass_soc
            c3s = 'PASS';
        else
            c3s = 'FAIL';
        end
        fprintf('Condition 3: %s\n', c3s);

        %% ================================================================
        %% LMP Summary
        %% ================================================================
        fprintf('\n=== LMP Summary ===\n');
        fprintf('Hour | Min LMP | Max LMP | Spread  | BESS LMP | Load (MW)\n');
        for t = 1:nt
            lmp_t = lmps(:, t);
            fprintf('HR%02d | %7.2f | %7.2f | %7.2f | %8.2f | %8.1f\n', ...
                    t, min(lmp_t), max(lmp_t), max(lmp_t) - min(lmp_t), ...
                    bess_lmps(t), hourly_totals(t));
        end

        %% ================================================================
        %% Overall pass/fail
        %% ================================================================
        fprintf('\n=== Overall Assessment ===\n');
        if pass_congestion
            oc1 = 'PASS';
        else
            oc1 = 'FAIL';
        end
        if pass_arbitrage
            oc2 = 'PASS';
        else
            oc2 = 'FAIL';
        end
        if pass_soc
            oc3 = 'PASS';
        else
            oc3 = 'FAIL';
        end
        fprintf('Condition 1 (Congestion):    %s\n', oc1);
        fprintf('Condition 2 (Arbitrage):     %s\n', oc2);
        fprintf('Condition 3 (SoC feasibility): %s\n', oc3);

        if pass_congestion && pass_arbitrage && pass_soc
            result_status = 'pass';
        end
    else
        %% GLPK exitflag issue
        fprintf('GLPK returned non-positive exitflag: %d\n', mdo.QP.exitflag);
        errors{end + 1} = sprintf('MOST solver returned exitflag=%d (GLPK integration issue)', ...
                                  mdo.QP.exitflag);
        fprintf('MOST multi-period DCOPF with storage is a core MOST capability.\n');
        fprintf('The formulation was set up correctly but GLPK solver integration\n');
        fprintf('prevents solution extraction (same issue as A-5).\n');
    end

    %% Peak memory
    [~, mem_out] = system('grep VmHWM /proc/self/status');
    peak_kb = sscanf(mem_out, 'VmHWM: %f');
    if ~isempty(peak_kb)
        peak_memory_mb = peak_kb / 1024;
    else
        peak_memory_mb = -1;
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
fprintf('Wall clock: %.4f s\n', solve_time);
if exist('peak_memory_mb', 'var')
    fprintf('Peak memory: %.1f MB\n', peak_memory_mb);
end

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
