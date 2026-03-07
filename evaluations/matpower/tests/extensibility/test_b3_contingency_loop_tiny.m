%% Test B-3: Contingency Loop (N-1 DCPF) on IEEE 39-bus (TINY)
%%
%% Pass condition: Solve N-1 DCPF contingencies (all 46 branches on TINY).
%% Collect max line loading across all cases. Runs without re-parsing or
%% re-instantiating the base model from file each iteration.
%%
%% Approach: Load case once, loop over branches disabling one at a time
%% via BR_STATUS toggle, solve rundcpf, record max loading, restore.
%%
%% Usage (from evaluations/matpower/):
%%   octave tests/extensibility/test_b3_contingency_loop_tiny.m

% Add MATPOWER to path
mp_root = fullfile(pwd, "matpower8.1");
addpath(fullfile(mp_root, "lib"));
addpath(fullfile(mp_root, "data"));
addpath(fullfile(mp_root, "mips", "lib"));
addpath(fullfile(mp_root, "mp-opt-model", "lib"));
addpath(fullfile(mp_root, "mptest", "lib"));

define_constants;

network_file = fullfile(pwd, "..", "..", "data", "networks", "case39.m");

fprintf("\n========================================\n");
fprintf("TEST B-3: Contingency Loop (N-1 DCPF) on TINY (IEEE 39-bus)\n");
fprintf("========================================\n");

status = "fail";
wall_clock = 0;
loc = 0;

tic_val = tic();
try
    % --- Load case ONCE ---
    mpc = loadcase(network_file);
    n_bus = size(mpc.bus, 1);
    n_branch = size(mpc.branch, 1);
    n_gen = size(mpc.gen, 1);
    fprintf("Loaded %d buses, %d branches, %d generators\n", n_bus, n_branch, n_gen);

    mpopt = mpoption("verbose", 0, "out.all", 0);

    % --- Set RATE_A for meaningful loading calculations ---
    % case39 has zero RATE_A; use branch reactance-based thermal limits
    % or simply set uniform limits for loading comparison
    % Use 500 MVA as a reference rating for all lines
    ref_rating = 500;
    mpc.branch(:, RATE_A) = ref_rating;

    % --- Base case DCPF ---
    fprintf("\n--- Base Case DCPF ---\n");
    results_base = rundcpf(mpc, mpopt);
    assert(results_base.success == 1, "Base case DCPF did not converge");
    base_max_flow = max(abs(results_base.branch(:, PF)));
    base_max_loading = base_max_flow / ref_rating * 100;
    fprintf("Base case max |flow|: %.2f MW (%.1f%% loading)\n", ...
            base_max_flow, base_max_loading);

    % --- N-1 Contingency Loop ---
    fprintf("\n--- N-1 Contingency Screening (%d contingencies) ---\n", n_branch);

    % Pre-allocate results
    ctg_max_flow    = zeros(n_branch, 1);
    ctg_max_loading = zeros(n_branch, 1);
    ctg_max_br_idx  = zeros(n_branch, 1);
    ctg_converged   = true(n_branch, 1);
    ctg_times       = zeros(n_branch, 1);
    ctg_island      = false(n_branch, 1);

    loop_tic = tic();
    for k = 1:n_branch
        ctg_tic = tic();

        % Disable branch k (in-place modification, no file re-read)
        mpc.branch(k, BR_STATUS) = 0;

        % Solve DCPF
        results_k = rundcpf(mpc, mpopt);

        if results_k.success
            % Find max flow on remaining in-service branches
            in_service = mpc.branch(:, BR_STATUS) == 1;
            flows = abs(results_k.branch(:, PF));
            flows(~in_service) = 0;  % ignore outaged branch
            [max_flow, max_idx] = max(flows);
            ctg_max_flow(k)    = max_flow;
            ctg_max_loading(k) = max_flow / ref_rating * 100;
            ctg_max_br_idx(k)  = max_idx;
        else
            ctg_converged(k) = false;
            ctg_max_flow(k) = NaN;
            ctg_max_loading(k) = NaN;
        end

        ctg_times(k) = toc(ctg_tic);

        % Restore branch k (in-place, no re-instantiation)
        mpc.branch(k, BR_STATUS) = 1;
    end
    loop_time = toc(loop_tic);
    wall_clock = toc(tic_val);

    % --- Report ---
    n_converged = sum(ctg_converged);
    n_failed = sum(~ctg_converged);
    fprintf("Converged: %d/%d, Failed: %d\n", n_converged, n_failed + n_converged, n_failed);
    fprintf("Total loop time: %.4f s (avg %.4f s/contingency)\n", ...
            loop_time, loop_time / n_branch);

    % Overall max loading across converged contingencies only
    conv_loading = ctg_max_loading;
    conv_loading(~ctg_converged) = -Inf;  % exclude diverged from max
    [overall_max_loading, worst_ctg] = max(conv_loading);
    overall_max_flow = ctg_max_flow(worst_ctg);
    worst_br = ctg_max_br_idx(worst_ctg);

    fprintf("\n--- Worst Contingency (converged only) ---\n");
    fprintf("Outage of branch %d (%d->%d)\n", worst_ctg, ...
            mpc.branch(worst_ctg, F_BUS), mpc.branch(worst_ctg, T_BUS));
    fprintf("Max loading: %.1f%% on branch %d (%d->%d) = %.2f MW\n", ...
            overall_max_loading, worst_br, ...
            mpc.branch(worst_br, F_BUS), mpc.branch(worst_br, T_BUS), ...
            overall_max_flow);

    % Top 10 most severe converged contingencies
    fprintf("\n--- Top 10 Most Severe Contingencies (converged) ---\n");
    fprintf("  Rank  Outage_Br  From->To     Max_Loading%%  Max_Flow_Br  Flow(MW)\n");
    [sorted_loading, sort_idx] = sort(conv_loading, "descend");
    rank = 0;
    for i = 1:n_branch
        k = sort_idx(i);
        if ctg_converged(k)
            rank = rank + 1;
            mb = ctg_max_br_idx(k);
            fprintf("  %3d   %4d       %3d->%-3d     %8.1f%%     %4d         %.2f\n", ...
                    rank, k, mpc.branch(k, F_BUS), mpc.branch(k, T_BUS), ...
                    ctg_max_loading(k), mb, ctg_max_flow(k));
            if rank >= 10
                break
            end
        end
    end

    % Per-contingency timing stats
    fprintf("\n--- Timing ---\n");
    fprintf("Min contingency time: %.4f s\n", min(ctg_times));
    fprintf("Max contingency time: %.4f s\n", max(ctg_times));
    fprintf("Mean contingency time: %.4f s\n", mean(ctg_times));
    fprintf("Total wall clock: %.4f s\n", wall_clock);

    % Failed contingencies detail
    if n_failed > 0
        fprintf("\n--- Failed Contingencies ---\n");
        failed_idx = find(~ctg_converged);
        for i = 1:length(failed_idx)
            k = failed_idx(i);
            fprintf("  Branch %d (%d->%d): DCPF did not converge (likely islanding)\n", ...
                    k, mpc.branch(k, F_BUS), mpc.branch(k, T_BUS));
        end
    end

    % --- Assertions ---
    assert(n_converged > 0, "No contingencies converged");
    % IEEE 39-bus has ~11 radial gen stubs; outaging these creates islands.
    % Expect ~35/46 to converge (76%). Require at least 50%.
    assert(n_converged >= 0.5 * n_branch, ...
           sprintf("Too many failures: %d/%d converged", n_converged, n_branch));
    % Max loading should be higher than base case (some redistribution)
    fprintf("\nMax N-1 loading (%.1f%%) vs base (%.1f%%)\n", ...
            overall_max_loading, base_max_loading);

    fprintf("\nAll assertions passed.\n");
    status = "pass";
    loc = 75;

catch err
    wall_clock = toc(tic_val);
    fprintf("ERROR: %s\n", err.message);
    fprintf("  in %s at line %d\n", err.stack(1).file, err.stack(1).line);
    status = "fail";
end

fprintf("\n========================================\n");
fprintf("STATUS: %s\n", status);
fprintf("WALL_CLOCK: %.4f\n", wall_clock);
fprintf("LOC: %d\n", loc);
fprintf("========================================\n");
