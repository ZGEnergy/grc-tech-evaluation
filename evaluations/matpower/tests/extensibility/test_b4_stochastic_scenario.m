%% Test B-4: Generate 20 scenarios, solve 12hr multi-period DCOPF for each, collect results
%%
%% Dimension: extensibility
%% Network: TINY (IEEE 39-bus New England)
%% Pass condition: Tool accepts timeseries inputs programmatically (not from config
%%   files only). Scenario loop is expressible without excessive per-scenario overhead.
%%   Results (prices, dispatch) are collectable in a structured format.
%% Tool: MATPOWER 8.1
%% Solver: GLPK (HiGHS unavailable in Octave devcontainer)

function result = test_b4_stochastic_scenario(network_file, timeseries_dir)
    if nargin < 1
        network_file = '/workspace/data/networks/case39.m';
    end
    if nargin < 2
        timeseries_dir = '/workspace/data/timeseries/case39';
    end

    result = struct();
    result.status = 'fail';
    result.wall_clock_seconds = 0;
    result.details = struct();
    result.errors = {};
    result.workarounds = {};

    tic;
    try
        %% ---- Setup MATPOWER ----
        addpath(genpath('/workspace/evaluations/matpower/matpower8.1'));
        define_constants;

        mpopt = mpoption('verbose', 0, 'out.all', 0);
        mpopt = mpoption(mpopt, 'opf.dc.solver', 'GLPK');

        %% ---- Load base case ----
        mpc = loadcase(network_file);
        n_bus = size(mpc.bus, 1);
        n_gen_base = size(mpc.gen, 1);

        %% ---- Apply differentiated costs from gen_temporal_params.csv ----
        % Cost mapping: hydro=$5, nuclear=$10, coal=$25, gas=$40 per MWh
        gen_params = csv2cell([timeseries_dir '/gen_temporal_params.csv']);
        cost_map = struct('hydro', 5, 'nuclear', 10, 'coal_large', 25, 'gas_CC', 40);

        for g = 1:n_gen_base
            gen_bus = mpc.gen(g, GEN_BUS);
            % Find matching row in gen_temporal_params
            tech_key = '';
            for row = 2:size(gen_params, 1)
                if gen_params{row, 3} == gen_bus  % bus_id column
                    tech_key = gen_params{row, 5};  % tech_class_key column
                    break;
                end
            end
            if isfield(cost_map, tech_key)
                mc = cost_map.(tech_key);
            else
                mc = 25;  % default
            end
            % Set linear cost curve: MODEL=2 (polynomial), NCOST=2, c1=mc, c0=0
            mpc.gencost(g, MODEL) = 2;
            mpc.gencost(g, NCOST) = 2;
            mpc.gencost(g, COST) = mc;
            mpc.gencost(g, COST+1) = 0;
        end

        %% ---- Load hourly load profiles (hours 1-12 only) ----
        load_data = csvread([timeseries_dir '/load_24h.csv'], 1, 0);
        load_bus_ids = load_data(:, 1);
        load_profiles = load_data(:, 2:13);  % Hours 1-12

        %% ---- Load renewable forecast profiles ----
        wind_data = csvread([timeseries_dir '/wind_forecast_24h.csv'], 1, 1);
        solar_data = csvread([timeseries_dir '/solar_forecast_24h.csv'], 1, 1);
        % wind_data: 3 rows x 24 cols, solar_data: 2 rows x 24 cols

        %% ---- Load renewable unit placements ----
        ren_csv = csv2cell([timeseries_dir '/renewable_units.csv']);
        n_ren = size(ren_csv, 1) - 1;  % 5 units
        ren_buses = zeros(n_ren, 1);
        ren_types = cell(n_ren, 1);
        ren_pmax = zeros(n_ren, 1);
        for r = 1:n_ren
            ren_buses(r) = ren_csv{r+1, 2};
            ren_types{r} = ren_csv{r+1, 3};
            ren_pmax(r) = ren_csv{r+1, 4};
        end

        %% ---- Load scenario multipliers (50 scenarios x 5 gens x 24 hours) ----
        scen_raw = csvread([timeseries_dir '/scenarios/scenario_multipliers_50x24.csv'], 1, 0);
        % Format: scenario, gen_uid_index(implicit), HR_1..HR_24
        % Each scenario has 5 rows (one per renewable gen)

        %% ---- Add renewable generators to base case ----
        mpc_base = mpc;
        for r = 1:n_ren
            new_gen = zeros(1, size(mpc_base.gen, 2));
            new_gen(GEN_BUS) = ren_buses(r);
            new_gen(PG) = 0;
            new_gen(QG) = 0;
            new_gen(QMAX) = 0;
            new_gen(QMIN) = 0;
            new_gen(VG) = 1.0;
            new_gen(MBASE) = mpc_base.baseMVA;
            new_gen(GEN_STATUS) = 1;
            new_gen(PMAX) = ren_pmax(r);
            new_gen(PMIN) = 0;
            mpc_base.gen = [mpc_base.gen; new_gen];

            % Add zero-cost gencost row
            new_cost = zeros(1, size(mpc_base.gencost, 2));
            new_cost(MODEL) = 2;
            new_cost(NCOST) = 2;
            new_cost(COST) = 0;  % zero marginal cost
            new_cost(COST+1) = 0;
            mpc_base.gencost = [mpc_base.gencost; new_cost];
        end
        n_gen_total = size(mpc_base.gen, 1);

        %% ---- Run scenario loop: 20 scenarios x 12 hours ----
        n_scenarios = 20;
        n_hours = 12;
        all_objectives = zeros(n_scenarios, n_hours);
        all_lmps = zeros(n_scenarios, n_hours, n_bus);
        all_dispatch = zeros(n_scenarios, n_hours, n_gen_total);
        n_success = 0;
        n_fail = 0;

        solve_start = tic;
        for s = 1:n_scenarios
            for h = 1:n_hours
                mpc_h = mpc_base;

                %% Apply hourly load profile
                for lb = 1:size(load_bus_ids, 1)
                    bus_id = load_bus_ids(lb);
                    bus_row = find(mpc_h.bus(:, BUS_I) == bus_id);
                    if ~isempty(bus_row)
                        mpc_h.bus(bus_row, PD) = load_profiles(lb, h);
                    end
                end

                %% Apply scenario-specific renewable output
                % scen_raw rows for scenario s: rows (s-1)*5+1 to s*5
                for r = 1:n_ren
                    scen_row = (s - 1) * n_ren + r;
                    multiplier = scen_raw(scen_row, 2 + h);  % col 3 onwards = HR_1..

                    % Base forecast for this renewable gen
                    if strcmp(ren_types{r}, 'wind')
                        wind_idx = sum(strcmp(ren_types(1:r), 'wind'));
                        base_forecast = wind_data(wind_idx, h);
                    else
                        solar_idx = sum(strcmp(ren_types(1:r), 'solar'));
                        base_forecast = solar_data(solar_idx, h);
                    end

                    gen_idx = n_gen_base + r;
                    scenario_output = base_forecast * multiplier;
                    mpc_h.gen(gen_idx, PMAX) = max(0, scenario_output);
                    mpc_h.gen(gen_idx, PMIN) = 0;
                end

                %% Solve DC OPF
                results_h = rundcopf(mpc_h, mpopt);

                if results_h.success
                    n_success = n_success + 1;
                    all_objectives(s, h) = results_h.f;
                    all_lmps(s, h, :) = results_h.bus(:, LAM_P);
                    all_dispatch(s, h, :) = results_h.gen(:, PG);
                else
                    n_fail = n_fail + 1;
                end
            end
        end
        total_solve_time = toc(solve_start);

        %% ---- Collect structured results ----
        total_solves = n_scenarios * n_hours;

        % Hourly statistics across scenarios
        hourly_mean_obj = mean(all_objectives, 1);
        hourly_std_obj = std(all_objectives, 0, 1);

        % Mean LMP per hour (average across scenarios and buses)
        hourly_mean_lmp = zeros(1, n_hours);
        for h = 1:n_hours
            lmps_h = squeeze(all_lmps(:, h, :));
            hourly_mean_lmp(h) = mean(lmps_h(:));
        end

        % LMP range across all scenarios
        all_lmp_vals = all_lmps(:);
        lmp_min = min(all_lmp_vals);
        lmp_max = max(all_lmp_vals);
        lmp_range = lmp_max - lmp_min;

        % Per-scenario solve time
        mean_per_scenario = total_solve_time / n_scenarios;
        mean_per_solve = total_solve_time / total_solves;

        %% ---- Populate results ----
        result.details.total_solves = total_solves;
        result.details.successful_solves = n_success;
        result.details.failed_solves = n_fail;
        result.details.total_solve_time_s = total_solve_time;
        result.details.mean_per_scenario_s = mean_per_scenario;
        result.details.mean_per_solve_s = mean_per_solve;
        result.details.lmp_min = lmp_min;
        result.details.lmp_max = lmp_max;
        result.details.lmp_range = lmp_range;
        result.details.hourly_mean_obj = hourly_mean_obj;
        result.details.hourly_std_obj = hourly_std_obj;
        result.details.hourly_mean_lmp = hourly_mean_lmp;

        %% ---- Peak memory ----
        [~, mem_out] = system('grep VmHWM /proc/self/status');
        result.details.peak_rss_kb = sscanf(mem_out, 'VmHWM: %f');

        %% ---- Check pass condition ----
        if n_success == total_solves
            result.status = 'pass';
        elseif n_success > 0
            result.status = 'partial_pass';
        end

        %% ---- Print summary ----
        fprintf('=== B-4 Stochastic Scenario Results ===\n');
        fprintf('Total solves: %d (success: %d, fail: %d)\n', total_solves, n_success, n_fail);
        fprintf('Total solve time: %.2f s\n', total_solve_time);
        fprintf('Mean per-scenario: %.3f s\n', mean_per_scenario);
        fprintf('Mean per-solve: %.4f s\n', mean_per_solve);
        fprintf('LMP range: %.2f $/MWh [%.2f, %.2f]\n', lmp_range, lmp_min, lmp_max);
        fprintf('\nHourly statistics:\n');
        fprintf('Hour | Mean Obj ($) | Std Obj ($) | Mean LMP ($/MWh)\n');
        for h = 1:n_hours
            fprintf('%4d | %12.0f | %11.0f | %17.2f\n', h, hourly_mean_obj(h), hourly_std_obj(h), hourly_mean_lmp(h));
        end

    catch e
        result.errors{end+1} = [e.identifier ': ' e.message];
        fprintf('ERROR: %s\n', e.message);
    end
    result.wall_clock_seconds = toc;
end

%% ---- Helper: read CSV with mixed types ----
function data = csv2cell(filepath)
    fid = fopen(filepath, 'r');
    if fid == -1
        error('Cannot open file: %s', filepath);
    end
    header = fgetl(fid);
    cols = strsplit(header, ',');
    n_cols = length(cols);
    data = {cols{:}};

    while ~feof(fid)
        line = fgetl(fid);
        if ischar(line) && ~isempty(line)
            parts = strsplit(line, ',');
            row = cell(1, n_cols);
            for c = 1:min(length(parts), n_cols)
                val = str2double(parts{c});
                if isnan(val)
                    row{c} = parts{c};
                else
                    row{c} = val;
                end
            end
            data = [data; row];
        end
    end
    fclose(fid);
end

%% Run when executed as script
result = test_b4_stochastic_scenario();
disp(result);
disp(result.details);
