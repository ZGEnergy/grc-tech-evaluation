%% Test A-4: AC Feasibility Check on DC OPF Dispatch — IEEE 39-bus (TINY)
%%
%% Pass condition: Take DC OPF dispatch, run full ACPF on that dispatch.
%% Achievable within the same model context. Voltage and thermal violations
%% identifiable from results.
%%
%% Usage (from evaluations/matpower/):
%%   octave tests/expressiveness/test_a4_ac_feasibility_tiny.m

% Add MATPOWER to path
mp_root = fullfile(pwd, "matpower8.1");
addpath(fullfile(mp_root, "lib"));
addpath(fullfile(mp_root, "data"));
addpath(fullfile(mp_root, "mips", "lib"));
addpath(fullfile(mp_root, "mp-opt-model", "lib"));
addpath(fullfile(mp_root, "mptest", "lib"));

% Load column index constants
define_constants;

% Load shared network
network_file = fullfile(pwd, "..", "..", "data", "networks", "case39.m");

fprintf("\n========================================\n");
fprintf("TEST A-4: AC Feasibility on DCOPF Dispatch (TINY)\n");
fprintf("========================================\n");

status = "fail";
wall_clock = 0;
loc = 0;

tic_val = tic();
try
    % --- Step 1: Solve DC OPF ---
    mpc = loadcase(network_file);
    fprintf("Loaded %d buses, %d branches, %d generators\n", ...
            size(mpc.bus, 1), size(mpc.branch, 1), size(mpc.gen, 1));

    mpopt = mpoption("verbose", 0, "out.all", 0);
    results_dc = rundcopf(mpc, mpopt);
    if ~results_dc.success
        error("DC OPF did not converge");
    end
    fprintf("DC OPF converged: YES (obj=%.2f $/hr)\n", results_dc.f);
    fprintf("DC OPF total dispatch: %.2f MW\n", sum(results_dc.gen(:, PG)));

    % --- Step 2: Fix generator dispatch to DC OPF solution ---
    % We modify the same mpc struct — no export/reimport needed.
    % Strategy: Set each generator's PG to the DC OPF dispatch value,
    % and also adjust PMIN=PMAX=PG to lock in the dispatch.
    % The slack bus generator will absorb any real power mismatch
    % (losses in AC that don't exist in DC).
    mpc_ac = mpc;  % start from original case (fresh voltages)
    dc_pg = results_dc.gen(:, PG);

    fprintf("\n--- Fixing dispatch from DC OPF ---\n");
    ng = size(mpc_ac.gen, 1);

    % Find the slack/reference bus generator
    slack_bus_idx = find(mpc_ac.bus(:, BUS_TYPE) == REF);
    slack_gen_idx = find(mpc_ac.gen(:, GEN_BUS) == mpc_ac.bus(slack_bus_idx(1), BUS_I));

    fprintf("Slack bus: %d (gen #%d)\n", mpc_ac.bus(slack_bus_idx(1), BUS_I), slack_gen_idx(1));

    % Fix all non-slack generators to DC OPF dispatch
    for g = 1:ng
        if g == slack_gen_idx(1)
            % Leave slack generator free to absorb losses
            mpc_ac.gen(g, PG) = dc_pg(g);
            fprintf("  Gen %2d (bus %2d): PG=%.2f MW [SLACK - free to adjust]\n", ...
                    g, mpc_ac.gen(g, GEN_BUS), dc_pg(g));
        else
            % Convert non-slack PV buses to PQ by fixing dispatch
            mpc_ac.gen(g, PG) = dc_pg(g);
            mpc_ac.gen(g, PMIN) = dc_pg(g);
            mpc_ac.gen(g, PMAX) = dc_pg(g);
            fprintf("  Gen %2d (bus %2d): PG=%.2f MW [FIXED]\n", ...
                    g, mpc_ac.gen(g, GEN_BUS), dc_pg(g));
        end
    end

    % --- Step 3: Run AC Power Flow ---
    fprintf("\nRunning AC Power Flow with fixed dispatch...\n");
    mpopt_pf = mpoption("verbose", 0, "out.all", 0, "pf.enforce_q_lims", 1);
    results_ac = runpf(mpc_ac, mpopt_pf);

    if ~results_ac.success
        fprintf("AC PF did NOT converge\n");
        converges_ac = false;
    else
        fprintf("AC PF converged: YES\n");
        converges_ac = true;
    end

    % --- Step 4: Check voltage violations ---
    fprintf("\n--- Voltage Analysis ---\n");
    vm = results_ac.bus(:, VM);
    vmin_lim = 0.95;
    vmax_lim = 1.05;

    v_low = find(vm < vmin_lim);
    v_high = find(vm > vmax_lim);
    n_v_violations = length(v_low) + length(v_high);

    fprintf("Voltage range: [%.4f, %.4f] p.u.\n", min(vm), max(vm));
    fprintf("Voltage limit band: [%.2f, %.2f] p.u.\n", vmin_lim, vmax_lim);

    if ~isempty(v_low)
        fprintf("LOW voltage violations (%d):\n", length(v_low));
        for k = 1:length(v_low)
            fprintf("  Bus %d: Vm=%.4f (below %.2f)\n", ...
                    results_ac.bus(v_low(k), BUS_I), vm(v_low(k)), vmin_lim);
        end
    end
    if ~isempty(v_high)
        fprintf("HIGH voltage violations (%d):\n", length(v_high));
        for k = 1:length(v_high)
            fprintf("  Bus %d: Vm=%.4f (above %.2f)\n", ...
                    results_ac.bus(v_high(k), BUS_I), vm(v_high(k)), vmax_lim);
        end
    end
    if n_v_violations == 0
        fprintf("No voltage violations.\n");
    end

    % --- Step 5: Check thermal violations ---
    fprintf("\n--- Thermal Limit Analysis ---\n");
    % Compute apparent power flow at each end
    sf = sqrt(results_ac.branch(:, PF).^2 + results_ac.branch(:, QF).^2);
    st = sqrt(results_ac.branch(:, PT).^2 + results_ac.branch(:, QT).^2);
    s_max = max(sf, st);
    rate_a = results_ac.branch(:, RATE_A);

    % Only check branches with nonzero RATE_A
    has_limit = rate_a > 0;
    thermal_violation = has_limit & (s_max > rate_a);
    n_thermal = sum(thermal_violation);

    fprintf("Branches with RATE_A limits: %d / %d\n", sum(has_limit), size(results_ac.branch, 1));
    if n_thermal > 0
        fprintf("THERMAL violations (%d):\n", n_thermal);
        viol_idx = find(thermal_violation);
        for k = 1:length(viol_idx)
            bi = viol_idx(k);
            fprintf("  Branch %d (%d->%d): S=%.2f MVA, RATE_A=%.0f MVA (%.1f%%)\n", ...
                    bi, results_ac.branch(bi, F_BUS), results_ac.branch(bi, T_BUS), ...
                    s_max(bi), rate_a(bi), 100 * s_max(bi) / rate_a(bi));
        end
    else
        fprintf("No thermal violations.\n");
    end

    % --- Step 6: Show top loaded branches ---
    fprintf("\n--- Top 5 loaded branches (by %% of RATE_A) ---\n");
    loading = zeros(size(rate_a));
    loading(has_limit) = 100 * s_max(has_limit) ./ rate_a(has_limit);
    [sorted_load, sort_idx] = sort(loading, "descend");
    for k = 1:min(5, length(sort_idx))
        bi = sort_idx(k);
        if loading(bi) > 0
            fprintf("  Branch %d (%d->%d): %.1f%% (%.2f / %.0f MVA)\n", ...
                    bi, results_ac.branch(bi, F_BUS), results_ac.branch(bi, T_BUS), ...
                    loading(bi), s_max(bi), rate_a(bi));
        end
    end

    % --- Step 7: Power balance check ---
    fprintf("\n--- Power Balance ---\n");
    total_gen_p = sum(results_ac.gen(:, PG));
    total_load_p = sum(results_ac.bus(:, PD));
    total_loss = total_gen_p - total_load_p;
    slack_pg = results_ac.gen(slack_gen_idx(1), PG);
    fprintf("Total generation: %.2f MW\n", total_gen_p);
    fprintf("Total load:       %.2f MW\n", total_load_p);
    fprintf("Total losses:     %.2f MW (%.2f%%)\n", total_loss, 100 * total_loss / total_load_p);
    fprintf("Slack gen PG:     %.2f MW (DC was %.2f MW)\n", slack_pg, dc_pg(slack_gen_idx(1)));
    fprintf("Slack adjustment: %.2f MW (absorbs AC losses)\n", slack_pg - dc_pg(slack_gen_idx(1)));

    % --- Summary ---
    wall_clock = toc(tic_val);
    fprintf("\n--- Summary ---\n");
    fprintf("AC PF converged: %s\n", mat2str(converges_ac));
    fprintf("Voltage violations: %d\n", n_v_violations);
    fprintf("Thermal violations: %d\n", n_thermal);
    fprintf("Wall clock: %.4f seconds\n", wall_clock);

    assert(converges_ac, "AC PF must converge");
    status = "pass";
    loc = 100;

catch err
    wall_clock = toc(tic_val);
    fprintf("ERROR: %s\n", err.message);
    status = "fail";
end

fprintf("\n========================================\n");
fprintf("STATUS: %s\n", status);
fprintf("WALL_CLOCK: %.4f\n", wall_clock);
fprintf("LOC: %d\n", loc);
fprintf("========================================\n");
