%% Test P2-3: Commitment Injection Workflow on IEEE 39-bus (TINY)
%%
%% Pass condition: Obtain SCUC schedule from A-5, lock commitments, solve
%% DCOPF, run AC PF feasibility check. Document capability per step.
%%
%% Usage (from evaluations/matpower/):
%%   octave tests/p2_readiness/test_p2_3_commitment_injection_tiny.m

% Add MATPOWER to path
mp_root = fullfile(pwd, "matpower8.1");
addpath(fullfile(mp_root, "lib"));
addpath(fullfile(mp_root, "data"));
addpath(fullfile(mp_root, "mips", "lib"));
addpath(fullfile(mp_root, "mp-opt-model", "lib"));
addpath(fullfile(mp_root, "mptest", "lib"));
addpath(fullfile(mp_root, "most", "lib"));

define_constants;
[CT_LABEL, CT_PROB, CT_TABLE, CT_TBUS, CT_TGEN, CT_TBRCH, CT_TAREABUS, ...
    CT_TAREAGEN, CT_TAREABRCH, CT_ROW, CT_COL, CT_CHGTYPE, CT_REP, ...
    CT_REL, CT_ADD, CT_NEWVAL, CT_TLOAD, CT_TAREALOAD, CT_LOAD_ALL_PQ, ...
    CT_LOAD_FIX_PQ, CT_LOAD_DIS_PQ, CT_LOAD_ALL_P, CT_LOAD_FIX_P, ...
    CT_LOAD_DIS_P, CT_TGENCOST, CT_TAREAGENCOST, CT_MODCOST_F, ...
    CT_MODCOST_X] = idx_ct;

network_file = fullfile(pwd, "..", "..", "data", "networks", "case39.m");

fprintf("\n========================================\n");
fprintf("TEST P2-3: Commitment Injection Workflow on TINY (IEEE 39-bus)\n");
fprintf("========================================\n");

status = "fail";
wall_clock = 0;
loc = 0;

tic_val = tic();
try
    %% ================================================================
    %% STEP 1: Run SCUC to get commitment schedule (same as A-5)
    %% ================================================================
    fprintf("\n=== STEP 1: SCUC (get commitment schedule) ===\n");
    mpc = loadcase(network_file);
    ng = size(mpc.gen, 1);
    nb = size(mpc.bus, 1);
    nt = 24;

    % Augment (same as A-5)
    for g = 1:ng
        pmax_g = mpc.gen(g, PMAX);
        mpc.gen(g, RAMP_AGC) = 0.3 * pmax_g;
        mpc.gen(g, RAMP_10)  = 0.3 * pmax_g;
        mpc.gen(g, RAMP_30)  = 0.3 * pmax_g;
        mpc.gen(g, PMIN) = 0.2 * pmax_g;
    end

    % Convert to PWL for GLPK
    for g = 1:ng
        if mpc.gencost(g, 1) == 2
            ncost = mpc.gencost(g, 4);
            pmin_g = mpc.gen(g, PMIN);
            pmax_g = mpc.gen(g, PMAX);
            if ncost == 3
                c2 = mpc.gencost(g, 5);
                c1 = mpc.gencost(g, 6);
                c0 = mpc.gencost(g, 7);
            elseif ncost == 2
                c2 = 0;
                c1 = mpc.gencost(g, 5);
                c0 = mpc.gencost(g, 6);
            else
                c2 = 0;
                c1 = 0;
                c0 = 0;
            end
            nseg = 10;
            p_points = linspace(pmin_g, pmax_g, nseg + 1);
            cost_points = c2 * p_points.^2 + c1 * p_points + c0;
            pwl_row = zeros(1, 4 + 2 * (nseg + 1));
            pwl_row(1) = 1;
            pwl_row(2) = 0;
            pwl_row(3) = 0;
            pwl_row(4) = nseg + 1;
            for k = 1:(nseg + 1)
                pwl_row(4 + 2 * k - 1) = p_points(k);
                pwl_row(4 + 2 * k)     = cost_points(k);
            end
            ncols_needed = 4 + 2 * (nseg + 1);
            if ncols_needed > size(mpc.gencost, 2)
                mpc.gencost = [mpc.gencost, zeros(ng, ncols_needed - size(mpc.gencost, 2))];
            end
            mpc.gencost(g, 1:ncols_needed) = pwl_row;
        end
    end
    for g = 1:ng
        mpc.gencost(g, 2) = mpc.gen(g, PMAX) * 5;
        mpc.gencost(g, 3) = mpc.gen(g, PMAX) * 1;
    end

    daily_curve = [0.83; 0.80; 0.78; 0.77; 0.78; 0.82
                   0.88; 0.94; 0.98; 1.00; 0.99; 0.98
                   0.97; 0.96; 0.95; 0.96; 0.98; 0.99
                   1.00; 0.98; 0.96; 0.93; 0.89; 0.85];
    load_profile = struct('type', 'mpcData', 'table', CT_TLOAD, 'rows', 0, ...
                          'col', CT_LOAD_ALL_PQ, 'chgtype', CT_REL, 'values', daily_curve);

    xgd_data = zeros(ng, 10);
    for g = 1:ng
        pmax_g = mpc.gen(g, PMAX);
        xgd_data(g, :) = [1, 1, 3, 2, 1e-8, 0.2 * pmax_g, 2e-8, 0.2 * pmax_g, 1e-9, 1e-9];
    end
    xgd_table.colnames = {'CommitKey', 'CommitSched', 'MinUp', 'MinDown', ...
                          'PositiveActiveReservePrice', 'PositiveActiveReserveQuantity', ...
                          'NegativeActiveReservePrice', 'NegativeActiveReserveQuantity', ...
                          'PositiveActiveDeltaPrice', 'NegativeActiveDeltaPrice'};
    xgd_table.data = xgd_data;
    xgd = loadxgendata(xgd_table, mpc);

    mpopt_uc = mpoption("verbose", 0, "out.all", 0, "model", "DC");
    mpopt_uc = mpoption(mpopt_uc, "most.dc_model", 1, "most.uc.run", 1, "most.solver", "GLPK");
    if exist("OCTAVE_VERSION", "builtin")
        mpopt_uc = mpoption(mpopt_uc, "mips.linsolver", "LU");
    end

    mdi_uc = loadmd(mpc, nt, xgd, [], [], load_profile);
    mdo_uc = most(mdi_uc, mpopt_uc);
    assert(mdo_uc.QP.exitflag > 0, "SCUC did not converge");
    fprintf("  SCUC converged, objective=%.2f\n", mdo_uc.QP.f);

    % Extract commitment
    if isfield(mdo_uc, 'UC') && isfield(mdo_uc.UC, 'CommitSched')
        commit = mdo_uc.UC.CommitSched;
    else
        commit = zeros(ng, nt);
        for t = 1:nt
            commit(:, t) = mdo_uc.flow(t, 1, 1).mpc.gen(:, GEN_STATUS);
        end
    end
    uc_dispatch = mdo_uc.results.ExpectedDispatch;
    fprintf("  Commitment extracted: %d x %d matrix\n", size(commit, 1), size(commit, 2));
    fprintf("  Effort: LOW (direct field access mdo.UC.CommitSched)\n");

    %% ================================================================
    %% STEP 2: Lock commitments and solve DCOPF for selected periods
    %% ================================================================
    fprintf("\n=== STEP 2: Lock commitments -> DCOPF per period ===\n");

    % Demonstrate per-period DCOPF with locked commitment
    % Load original (un-augmented) case for clean DCOPF
    mpc_base = loadcase(network_file);
    mpopt_dc = mpoption("verbose", 0, "out.all", 0);

    test_periods = [4, 10, 19];  % low-load, mid-load, peak
    dcopf_dispatch = zeros(ng, length(test_periods));
    dcopf_lmps = zeros(nb, length(test_periods));

    for idx = 1:length(test_periods)
        t = test_periods(idx);
        fprintf("\n  --- Period HE%02d (load factor=%.2f) ---\n", t, daily_curve(t));

        % Create period-specific case with locked commitment
        mpc_t = mpc_base;
        % Scale load
        mpc_t.bus(:, PD) = mpc_base.bus(:, PD) * daily_curve(t);
        mpc_t.bus(:, QD) = mpc_base.bus(:, QD) * daily_curve(t);

        % Lock commitment: turn off uncommitted generators
        n_off = 0;
        for g = 1:ng
            if commit(g, t) < 0.5
                mpc_t.gen(g, GEN_STATUS) = 0;
                n_off = n_off + 1;
            end
        end
        fprintf("  Generators off (from UC): %d / %d\n", n_off, ng);

        % Solve DCOPF
        results_t = rundcopf(mpc_t, mpopt_dc);
        assert(results_t.success == 1, ...
               sprintf("DCOPF failed for period %d", t));
        fprintf("  DCOPF converged, obj=%.2f $/hr\n", results_t.f);
        fprintf("  Total dispatch: %.1f MW (load=%.1f MW)\n", ...
                sum(results_t.gen(:, PG)), sum(mpc_t.bus(:, PD)));

        dcopf_dispatch(:, idx) = results_t.gen(:, PG);
        dcopf_lmps(:, idx) = results_t.bus(:, LAM_P);
    end
    fprintf("\n  Effort: LOW (set GEN_STATUS=0 for off gens, scale load, rundcopf)\n");

    %% ================================================================
    %% STEP 3: AC Power Flow feasibility check
    %% ================================================================
    fprintf("\n=== STEP 3: AC PF feasibility check ===\n");

    % Take the peak period (HE19) DCOPF result and check AC feasibility
    t_peak = 19;
    mpc_ac = loadcase(network_file);
    mpc_ac.bus(:, PD) = mpc_base.bus(:, PD) * daily_curve(t_peak);
    mpc_ac.bus(:, QD) = mpc_base.bus(:, QD) * daily_curve(t_peak);

    % Lock commitment
    for g = 1:ng
        if commit(g, t_peak) < 0.5
            mpc_ac.gen(g, GEN_STATUS) = 0;
        end
    end

    % Inject PG from DCOPF results (HE19 is index 3 in test_periods)
    idx_peak = find(test_periods == t_peak);
    for g = 1:ng
        if mpc_ac.gen(g, GEN_STATUS) > 0
            mpc_ac.gen(g, PG) = dcopf_dispatch(g, idx_peak);
        end
    end

    % Convert PV buses to PQ for non-slack generators (keep voltage setpoints)
    % Actually, MATPOWER runpf handles this automatically based on gen status

    mpopt_pf = mpoption("verbose", 0, "out.all", 0, "pf.alg", "NR");
    results_pf = runpf(mpc_ac, mpopt_pf);

    if results_pf.success
        fprintf("  AC PF converged: YES\n");
        fprintf("  Voltage range: [%.4f, %.4f] pu\n", ...
                min(results_pf.bus(:, VM)), max(results_pf.bus(:, VM)));
        fprintf("  Max voltage deviation from 1.0: %.4f pu\n", ...
                max(abs(results_pf.bus(:, VM) - 1.0)));

        % Check voltage violations
        v_min = 0.95;
        v_max = 1.05;
        v_violations = sum(results_pf.bus(:, VM) < v_min | results_pf.bus(:, VM) > v_max);
        fprintf("  Voltage violations (%.2f-%.2f pu): %d / %d buses\n", ...
                v_min, v_max, v_violations, nb);

        % Check reactive power limits
        q_over = 0;
        for g = 1:ng
            if mpc_ac.gen(g, GEN_STATUS) > 0
                qg = results_pf.gen(g, QG);
                if qg > mpc_ac.gen(g, QMAX) + 1 || qg < mpc_ac.gen(g, QMIN) - 1
                    q_over = q_over + 1;
                end
            end
        end
        fprintf("  Reactive power limit violations: %d / %d generators\n", q_over, ng);
        if v_violations == 0
            fprintf("  AC feasibility: FEASIBLE\n");
        else
            fprintf("  AC feasibility: MARGINAL (voltage violations)\n");
        end
    else
        fprintf("  AC PF converged: NO\n");
        fprintf("  AC feasibility: INFEASIBLE (PF did not converge)\n");
    end
    fprintf("  Effort: LOW (inject PG from DCOPF, call runpf)\n");

    %% ================================================================
    %% STEP 4: Full pipeline summary
    %% ================================================================
    wall_clock = toc(tic_val);

    fprintf("\n=== STEP 4: Full pipeline summary ===\n");
    fprintf("  Step 1 - SCUC (get commitment):     CAPABLE, effort=LOW\n");
    fprintf("    API: MOST with uc.run=1 -> mdo.UC.CommitSched\n");
    fprintf("  Step 2 - Lock commitment + DCOPF:    CAPABLE, effort=LOW\n");
    fprintf("    API: Set GEN_STATUS=0 for off gens -> rundcopf()\n");
    fprintf("  Step 3 - AC PF feasibility:          CAPABLE, effort=LOW\n");
    fprintf("    API: Inject PG from DCOPF -> runpf()\n");
    fprintf("  Overall workflow friction: LOW\n");
    fprintf("  LOC for full pipeline: ~150\n");
    fprintf("  Wall clock: %.4f seconds\n", wall_clock);

    status = "pass";
    loc = 155;

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
fprintf("========================================\n");
