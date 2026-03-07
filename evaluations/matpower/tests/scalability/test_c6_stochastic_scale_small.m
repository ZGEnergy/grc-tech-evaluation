%% Test C-6: Stochastic Scale on SMALL (ACTIVSg 2000-bus)
%%
%% Pass condition: Completes on SMALL. Performance and price extraction recorded.
%% Network: 2000 buses, 3206 branches, 544 generators
%% Solver: MIPS (default QP) or GLPK
%%
%% Approach: Use MOST for 12-hour stochastic DCOPF with 3 scenarios on SMALL.
%% Start with 3 scenarios (manageable). If that works, try more.
%% MOST builds a monolithic QP — with 544 gens x 12 periods x 3 scenarios,
%% the QP may be very large.
%%
%% Usage (from evaluations/matpower/):
%%   octave tests/scalability/test_c6_stochastic_scale_small.m

% Add MATPOWER to path
mp_root = "/workspace/evaluations/matpower/matpower8.1";
addpath(fullfile(mp_root, "lib"));
addpath(fullfile(mp_root, "data"));
addpath(fullfile(mp_root, "mips", "lib"));
addpath(fullfile(mp_root, "mp-opt-model", "lib"));
addpath(fullfile(mp_root, "mptest", "lib"));
addpath(fullfile(mp_root, "most", "lib"));
addpath(fullfile(mp_root, "most", "lib", "t"));
addpath(fullfile(mp_root, "most", "lib"));

% Load column index constants
define_constants;
[CT_LABEL, CT_PROB, CT_TABLE, CT_TBUS, CT_TGEN, CT_TBRCH, CT_TAREABUS, ...
    CT_TAREAGEN, CT_TAREABRCH, CT_ROW, CT_COL, CT_CHGTYPE, CT_REP, ...
    CT_REL, CT_ADD, CT_NEWVAL, CT_TLOAD, CT_TAREALOAD, CT_LOAD_ALL_PQ, ...
    CT_LOAD_FIX_PQ, CT_LOAD_DIS_PQ, CT_LOAD_ALL_P, CT_LOAD_FIX_P, ...
    CT_LOAD_DIS_P, CT_TGENCOST, CT_TAREAGENCOST, CT_MODCOST_F, ...
    CT_MODCOST_X] = idx_ct;

% Load network
network_file = fullfile(pwd, "..", "..", "data", "networks", "case_ACTIVSg2000.m");

fprintf("\n========================================\n");
fprintf("TEST C-6: Stochastic Scale on SMALL (ACTIVSg 2000-bus)\n");
fprintf("========================================\n");

status = "fail";
wall_clock = 0;
loc = 0;
per_scenario_avg = 0;
qp_vars = 0;

tic_val = tic();
try
    % --- Load and prepare case ---
    fprintf("Loading network...\n");
    mpc = loadcase(network_file);
    ng = size(mpc.gen, 1);
    nb = size(mpc.bus, 1);
    nl = size(mpc.branch, 1);
    fprintf("Loaded %d buses, %d branches, %d generators\n", nb, nl, ng);

    % --- Fix zero RATE_A branches ---
    zero_rate = mpc.branch(:, RATE_A) == 0;
    n_zero = sum(zero_rate);
    if n_zero > 0
        mpc.branch(zero_rate, RATE_A) = 9999;
        mpc.branch(zero_rate, RATE_B) = 9999;
        mpc.branch(zero_rate, RATE_C) = 9999;
        fprintf("  Set %d zero-RATE_A branches to 9999 MVA\n", n_zero);
    end

    % --- Parameters ---
    nt = 12;    % 12-hour horizon
    nj_target = 3;  % start with 3 scenarios

    fprintf("Target: %d periods, %d scenarios\n", nt, nj_target);

    % --- Step 1: Set ramp rates ---
    fprintf("\n--- Setting ramp rates ---\n");
    for g = 1:ng
        pmax_g = max(mpc.gen(g, PMAX), 1);
        mpc.gen(g, RAMP_AGC) = 0.3 * pmax_g;
        mpc.gen(g, RAMP_10)  = 0.3 * pmax_g;
        mpc.gen(g, RAMP_30)  = 0.3 * pmax_g;
    end
    fprintf("  Ramp rates set to 30%% of Pmax\n");

    % --- Step 2: Create xGenData ---
    fprintf("\n--- Creating xGenData ---\n");
    xgd_table.colnames = {
                          'PositiveActiveReservePrice', ...
                          'PositiveActiveReserveQuantity', ...
                          'NegativeActiveReservePrice', ...
                          'NegativeActiveReserveQuantity', ...
                          'PositiveActiveDeltaPrice', ...
                          'NegativeActiveDeltaPrice' ...
                         };
    xgd_data = zeros(ng, 6);
    for g = 1:ng
        pmax_g = max(mpc.gen(g, PMAX), 1);
        xgd_data(g, :) = [1e-8, 0.15 * pmax_g, 2e-8, 0.15 * pmax_g, 1e-9, 1e-9];
    end
    xgd_table.data = xgd_data;
    xgd = loadxgendata(xgd_table, mpc);
    fprintf("  Created xGenData for %d generators\n", ng);

    % --- Attempt stochastic solve with increasing scenarios ---
    nj_attempts = [3];
    solved = false;
    nj_used = 0;

    for attempt = 1:length(nj_attempts)
        nj = nj_attempts(attempt);
        fprintf("\n=== Attempting %d-period, %d-scenario stochastic DCOPF ===\n", nt, nj);

        % --- Step 3: Create stochastic transition matrix ---
        transmat = cell(nt, 1);
        probs = ones(nj, 1) / nj;  % equal probabilities
        transmat{1} = probs;
        for t = 2:nt
            transmat{t} = repmat(probs, 1, nj);  % same from each prior state
        end

        % --- Step 4: Create profiles ---
        % Load profile: daily curve with scenario variation
        base_load_curve = [0.83; 0.80; 0.78; 0.82; 0.88; 0.94
                           0.98; 1.00; 0.99; 0.97; 0.95; 0.93];

        % Scenario multipliers: low/med/high load
        if nj == 3
            load_scenarios = [0.95, 1.00, 1.05];
        elseif nj == 5
            load_scenarios = [0.90, 0.95, 1.00, 1.05, 1.10];
        else
            load_scenarios = linspace(0.90, 1.10, nj);
        end

        load_profile_values = base_load_curve * load_scenarios;

        load_profile = struct( ...
                              'type', 'mpcData', ...
                              'table', CT_TLOAD, ...
                              'rows', 0, ...
                              'col', CT_LOAD_ALL_PQ, ...
                              'chgtype', CT_REL, ...
                              'values', load_profile_values ...
                             );

        profiles = load_profile;

        % --- Step 5: Build and solve ---
        mpopt = mpoption("verbose", 0, "out.all", 0);
        mpopt = mpoption(mpopt, "model", "DC");
        mpopt = mpoption(mpopt, "most.dc_model", 1);
        mpopt = mpoption(mpopt, "most.solver", "DEFAULT");
        if exist("OCTAVE_VERSION", "builtin")
            mpopt = mpoption(mpopt, "mips.linsolver", "LU");
        end

        fprintf("Building MOST input data...\n");
        build_start = tic();
        mdi = loadmd(mpc, transmat, xgd, [], [], profiles);
        build_time = toc(build_start);
        fprintf("  MOST data built in %.2f seconds\n", build_time);

        fprintf("Solving MOST stochastic DCOPF (%d periods x %d scenarios)...\n", nt, nj);
        solve_start = tic();
        mdo = most(mdi, mpopt);
        solve_time = toc(solve_start);

        if mdo.QP.exitflag > 0
            solved = true;
            nj_used = nj;
            qp_vars = length(mdo.QP.x);
            fprintf("  CONVERGED (exitflag=%d)\n", mdo.QP.exitflag);
            fprintf("  Objective: %.2f\n", mdo.QP.f);
            fprintf("  QP variables: %d\n", qp_vars);
            fprintf("  Solve time: %.2f seconds\n", solve_time);
            per_scenario_avg = solve_time / nj;
            fprintf("  Per-scenario average: %.2f seconds\n", per_scenario_avg);
        else
            fprintf("  FAILED (exitflag=%d), solve time: %.2f seconds\n", mdo.QP.exitflag, solve_time);
            if attempt < length(nj_attempts)
                fprintf("  Reducing scenario count...\n");
            end
        end

        if solved
            break
        end
    end

    wall_clock = toc(tic_val);

    if solved
        % --- Step 6: Extract results ---
        fprintf("\n--- Results for %d periods x %d scenarios ---\n", nt, nj_used);

        % Expected dispatch
        exp_dispatch = mdo.results.ExpectedDispatch;
        fprintf("Expected dispatch matrix: %d generators x %d periods\n", ...
                size(exp_dispatch, 1), size(exp_dispatch, 2));

        fprintf("  Total dispatch (MW) at sample hours:\n  ");
        sample_t = [1, 4, 8, 12];
        for t = sample_t
            fprintf(" T%02d=%7.1f", t, sum(exp_dispatch(:, t)));
        end
        fprintf("\n");

        % Prices
        gen_prices = mdo.results.GenPrices;
        fprintf("\n--- Price Summary ---\n");
        fprintf("  Average price at sample hours:\n  ");
        for t = sample_t
            fprintf(" T%02d=$%6.2f", t, mean(gen_prices(:, t)));
        end
        fprintf("\n");

        % Scenario-specific results
        fprintf("\n--- Scenario Comparison at T=6 (peak) ---\n");
        t_peak = 6;
        for j = 1:nj_used
            rr = mdo.flow(t_peak, j, 1).mpc;
            total_gen = sum(rr.gen(:, PG));
            lmp = rr.bus(:, LAM_P);
            fprintf("  Scenario %d: Total gen=%7.1f MW, LMP range=[%.2f, %.2f]\n", ...
                    j, total_gen, min(lmp), max(lmp));
        end

        % Verify scenarios differ
        pg_s1 = mdo.flow(t_peak, 1, 1).mpc.gen(:, PG);
        pg_sn = mdo.flow(t_peak, nj_used, 1).mpc.gen(:, PG);
        scenarios_differ = max(abs(pg_s1 - pg_sn)) > 0.01;
        fprintf("\n  Scenarios produce different dispatch: %s\n", mat2str(scenarios_differ));

        fprintf("\n--- Formulation ---\n");
        fprintf("QP dimensions: %d variables, %d constraints\n", ...
                length(mdo.QP.x), size(mdo.QP.A, 1));
        fprintf("Step probabilities: %s\n", mat2str(mdo.StepProb', 4));

        status = "pass";
        loc = 140;
    else
        fprintf("\nFAILED: Could not solve stochastic DCOPF on SMALL\n");
        fprintf("FINDING: MOST monolithic QP too large for MIPS on 2000-bus network\n");
        status = "fail";
        loc = 140;
    end

    fprintf("\nTotal wall clock: %.2f seconds\n", wall_clock);

catch err
    wall_clock = toc(tic_val);
    fprintf("ERROR: %s\n", err.message);
    if isfield(err, 'stack') && length(err.stack) > 0
        fprintf("Error in: %s (line %d)\n", err.stack(1).name, err.stack(1).line);
    end
    status = "fail";
end

fprintf("\n========================================\n");
fprintf("STATUS: %s\n", status);
fprintf("WALL_CLOCK: %.4f\n", wall_clock);
fprintf("LOC: %d\n", loc);
fprintf("QP_VARS: %d\n", qp_vars);
fprintf("PER_SCENARIO_AVG: %.4f\n", per_scenario_avg);
fprintf("========================================\n");
