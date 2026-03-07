%% Test A-2: AC Power Flow (Newton-Raphson) on IEEE 39-bus (TINY)
%%
%% Pass condition: Converges. Bus voltage magnitudes and angles, line P/Q
%% flows, and losses accessible as structured output.
%%
%% Convergence protocol:
%%   1. Flat start (all V=1.0, all angles=0)
%%   2. If flat start fails -> DC warm start fallback
%%
%% Usage (from evaluations/matpower/):
%%   octave tests/expressiveness/test_a2_acpf_tiny.m

% Add MATPOWER to path
mp_root = fullfile(pwd, "matpower8.1");
addpath(fullfile(mp_root, "lib"));
addpath(fullfile(mp_root, "data"));
addpath(fullfile(mp_root, "mips", "lib"));
addpath(fullfile(mp_root, "mp-opt-model", "lib"));
addpath(fullfile(mp_root, "mptest", "lib"));

% Load shared network
network_file = fullfile(pwd, "..", "..", "data", "networks", "case39.m");

fprintf("\n========================================\n");
fprintf("TEST A-2: ACPF on TINY (IEEE 39-bus)\n");
fprintf("========================================\n");

status = "fail";
wall_clock = 0;
loc = 0;
start_method = "flat";

tic_val = tic();
try
    % --- Load case ---
    mpc = loadcase(network_file);
    fprintf("Loaded %d buses, %d branches, %d generators\n", ...
            size(mpc.bus, 1), size(mpc.branch, 1), size(mpc.gen, 1));

    % --- Configure solver: Newton-Raphson ---
    mpopt = mpoption("pf.alg", "NR", "verbose", 0, "out.all", 0);

    % --- Step 1: Flat start ---
    mpc_flat = mpc;
    mpc_flat.bus(:, 8) = 1.0;   % VM = 1.0 p.u.
    mpc_flat.bus(:, 9) = 0.0;   % VA = 0 degrees
    % Keep slack/PV bus voltage setpoints from gen data
    % (MATPOWER handles this internally via gen(:,6) VG)

    fprintf("\nAttempt 1: Flat start (V=1.0, theta=0)...\n");
    results = runpf(mpc_flat, mpopt);

    if ~results.success
        fprintf("Flat start did not converge. Trying DC warm start...\n");
        start_method = "dc_warm";

        % Step 2: DC warm start
        dc_results = rundcpf(mpc, mpopt);
        if dc_results.success
            mpc_warm = mpc;
            mpc_warm.bus(:, 9) = dc_results.bus(:, 9);  % use DC angles
            results = runpf(mpc_warm, mpopt);
        end
    end

    wall_clock = toc(tic_val);

    if ~results.success
        error("ACPF did not converge (tried flat start and DC warm start)");
    end

    fprintf("ACPF converged: YES (start method: %s)\n", start_method);
    fprintf("Wall clock: %.4f seconds\n", wall_clock);

    % --- Extract structured outputs ---

    % 1. Bus voltage magnitudes and angles
    bus_vm = results.bus(:, 8);  % VM
    bus_va = results.bus(:, 9);  % VA (degrees)
    bus_ids = results.bus(:, 1);

    fprintf("\n--- Bus Voltages ---\n");
    fprintf("  Bus   VM (pu)   VA (deg)\n");
    sample_buses = [1, 10, 20, 31, 39];
    for k = 1:length(sample_buses)
        idx = find(bus_ids == sample_buses(k));
        if ~isempty(idx)
            fprintf("  %3d   %7.4f   %8.4f\n", sample_buses(k), bus_vm(idx), bus_va(idx));
        end
    end
    fprintf("  VM range: [%.4f, %.4f] pu\n", min(bus_vm), max(bus_vm));
    fprintf("  VA range: [%.4f, %.4f] deg\n", min(bus_va), max(bus_va));

    % 2. Line P and Q flows
    pf = results.branch(:, 14);  % PF (from-end real)
    qf = results.branch(:, 15);  % QF (from-end reactive)
    pt = results.branch(:, 16);  % PT (to-end real)
    qt = results.branch(:, 17);  % QT (to-end reactive)

    fprintf("\n--- Line Flows (first 5 branches) ---\n");
    fprintf("  Br#  From  To     PF(MW)    QF(MVAr)   PT(MW)    QT(MVAr)\n");
    for k = 1:min(5, size(results.branch, 1))
        fprintf("  %3d  %4d  %4d  %8.2f  %8.2f  %8.2f  %8.2f\n", ...
                k, results.branch(k, 1), results.branch(k, 2), pf(k), qf(k), pt(k), qt(k));
    end
    fprintf("  ... (%d branches total)\n", size(results.branch, 1));

    % 3. Losses
    p_loss = pf + pt;  % per-branch real power loss
    q_loss = qf + qt;  % per-branch reactive power loss
    total_p_loss = sum(p_loss);
    total_q_loss = sum(q_loss);

    fprintf("\n--- Losses ---\n");
    fprintf("  Total P loss: %.4f MW\n", total_p_loss);
    fprintf("  Total Q loss: %.4f MVAr\n", total_q_loss);
    fprintf("  Loss %% of load: %.2f%%\n", 100 * total_p_loss / sum(results.bus(:, 3)));

    % 4. Generator dispatch
    fprintf("\n--- Generator Output ---\n");
    fprintf("  Gen#  Bus    PG(MW)    QG(MVAr)\n");
    for g = 1:size(results.gen, 1)
        fprintf("  %3d  %4d  %8.2f  %8.2f\n", g, results.gen(g, 1), results.gen(g, 2), results.gen(g, 3));
    end
    fprintf("  Total P gen: %.2f MW\n", sum(results.gen(:, 2)));
    fprintf("  Total Q gen: %.2f MVAr\n", sum(results.gen(:, 3)));

    % --- Verify outputs are non-trivial ---
    assert(all(bus_vm > 0), "Some bus voltages are zero or negative");
    assert(any(bus_va ~= 0), "All voltage angles are zero");
    assert(any(pf ~= 0), "All P flows are zero");
    assert(any(qf ~= 0), "All Q flows are zero");
    assert(total_p_loss >= 0, "Total P loss is negative");

    fprintf("\nAll structured outputs accessible: YES\n");
    status = "pass";
    loc = 70;

catch err
    wall_clock = toc(tic_val);
    fprintf("ERROR: %s\n", err.message);
    status = "fail";
end

fprintf("\n========================================\n");
fprintf("STATUS: %s\n", status);
fprintf("WALL_CLOCK: %.4f\n", wall_clock);
fprintf("START_METHOD: %s\n", start_method);
fprintf("LOC: %d\n", loc);
fprintf("========================================\n");
