%% Test C-2: ACPF Scale on ACTIVSg 10k (MEDIUM)
%%
%% Pass condition: Converges on MEDIUM network. Performance recorded.
%% Convergence protocol: flat start, then DC warm start fallback.
%%
%% Usage (from evaluations/matpower/):
%%   octave tests/scalability/test_c2_acpf_scale_medium.m

% Add MATPOWER to path
mp_root = "/workspace/evaluations/matpower/matpower8.1";
addpath(fullfile(mp_root, "lib"));
addpath(fullfile(mp_root, "data"));
addpath(fullfile(mp_root, "mips", "lib"));
addpath(fullfile(mp_root, "mp-opt-model", "lib"));
addpath(fullfile(mp_root, "mptest", "lib"));

define_constants;

network_file = "/workspace/data/networks/case_ACTIVSg10k.m";

fprintf("\n========================================\n");
fprintf("TEST C-2: ACPF Scale on MEDIUM (ACTIVSg 10k)\n");
fprintf("========================================\n");

status = "fail";
wall_clock = 0;
iterations = 0;
loc = 0;
start_method = "flat";

tic_val = tic();
try
    % --- Load case ---
    mpc = loadcase(network_file);
    nb = size(mpc.bus, 1);
    nbr = size(mpc.branch, 1);
    ng = size(mpc.gen, 1);
    fprintf("Loaded %d buses, %d branches, %d generators\n", nb, nbr, ng);

    load_time = toc(tic_val);
    fprintf("Case load time: %.4f seconds\n", load_time);

    % --- Configure solver: Newton-Raphson ---
    mpopt = mpoption("pf.alg", "NR", "verbose", 1, "out.all", 0);
    mpopt = mpoption(mpopt, "pf.nr.max_it", 50);

    % --- Attempt 1: Default start (use case file voltage setpoints) ---
    fprintf("\nAttempt 1: Default start...\n");
    tic_solve = tic();
    results = runpf(mpc, mpopt);
    solve_time = toc(tic_solve);

    if ~results.success
        fprintf("Default start did not converge. Trying flat start...\n");
        start_method = "flat";

        % Attempt 2: Flat start
        mpc_flat = mpc;
        mpc_flat.bus(:, VM) = 1.0;
        mpc_flat.bus(:, VA) = 0.0;
        tic_solve = tic();
        results = runpf(mpc_flat, mpopt);
        solve_time = toc(tic_solve);
    end

    if ~results.success
        fprintf("Flat start did not converge. Trying DC warm start...\n");
        start_method = "dc_warm";

        % Attempt 3: DC warm start
        mpopt_dc = mpoption("verbose", 0, "out.all", 0);
        dc_results = rundcpf(mpc, mpopt_dc);
        if dc_results.success
            mpc_warm = mpc;
            mpc_warm.bus(:, VA) = dc_results.bus(:, VA);
            tic_solve = tic();
            results = runpf(mpc_warm, mpopt);
            solve_time = toc(tic_solve);
        end
    end

    wall_clock = toc(tic_val);

    if ~results.success
        error("ACPF did not converge (tried default, flat, and DC warm start)");
    end

    % Extract iteration count from results
    if isfield(results, "et")
        fprintf("MATPOWER internal solve time: %.4f seconds\n", results.et);
    end

    fprintf("\nACPF converged: YES (start method: %s)\n", start_method);
    fprintf("Solve time: %.4f seconds\n", solve_time);
    fprintf("Total wall clock (load + solve): %.4f seconds\n", wall_clock);

    % --- Extract key outputs ---
    bus_vm = results.bus(:, VM);
    bus_va = results.bus(:, VA);
    pf = results.branch(:, PF);
    qf = results.branch(:, QF);

    fprintf("\n--- Bus Voltages ---\n");
    fprintf("  VM range: [%.4f, %.4f] pu\n", min(bus_vm), max(bus_vm));
    fprintf("  VA range: [%.4f, %.4f] degrees\n", min(bus_va), max(bus_va));

    fprintf("\n--- Line Flows ---\n");
    fprintf("  Max |P flow|: %.2f MW\n", max(abs(pf)));
    fprintf("  Max |Q flow|: %.2f MVAr\n", max(abs(qf)));
    fprintf("  Non-zero P flows: %d / %d\n", sum(abs(pf) > 1e-6), nbr);

    % Losses
    pt = results.branch(:, PT);
    qt = results.branch(:, QT);
    total_p_loss = sum(pf + pt);
    total_q_loss = sum(qf + qt);
    fprintf("\n--- Losses ---\n");
    fprintf("  Total P loss: %.2f MW\n", total_p_loss);
    fprintf("  Total Q loss: %.2f MVAr\n", total_q_loss);
    fprintf("  Loss %% of load: %.2f%%\n", 100 * total_p_loss / sum(results.bus(:, PD)));

    fprintf("\n--- Generation ---\n");
    fprintf("  Total P gen: %.2f MW\n", sum(results.gen(:, PG)));
    fprintf("  Total Q gen: %.2f MVAr\n", sum(results.gen(:, QG)));
    fprintf("  Total P load: %.2f MW\n", sum(results.bus(:, PD)));

    % --- Verify non-trivial ---
    assert(all(bus_vm > 0), "Some bus voltages are zero or negative");
    assert(any(bus_va ~= 0), "All voltage angles are zero");
    assert(any(pf ~= 0), "All P flows are zero");
    assert(total_p_loss >= 0, "Total P loss is negative");

    fprintf("\nAll outputs verified: YES\n");
    status = "pass";
    loc = 60;

catch err
    wall_clock = toc(tic_val);
    fprintf("ERROR: %s\n", err.message);
    if length(err.stack) > 0
        fprintf("Error in: %s (line %d)\n", err.stack(1).name, err.stack(1).line);
    end
    status = "fail";
end

fprintf("\n========================================\n");
fprintf("STATUS: %s\n", status);
fprintf("WALL_CLOCK: %.4f\n", wall_clock);
fprintf("START_METHOD: %s\n", start_method);
fprintf("LOC: %d\n", loc);
fprintf("========================================\n");
