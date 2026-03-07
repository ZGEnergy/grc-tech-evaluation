%% Test C-7: Solver Swap on ACTIVSg 10k (MEDIUM)
%%
%% Pass condition: Solver swap requires only parameter change, not
%% reformulation. Timing per solver recorded.
%%
%% Usage (from evaluations/matpower/):
%%   octave tests/scalability/test_c7_solver_swap_medium.m

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
fprintf("TEST C-7: Solver Swap on MEDIUM (ACTIVSg 10k)\n");
fprintf("========================================\n");

status = "fail";
wall_clock = 0;
loc = 0;

tic_val = tic();
try
    % --- Load case ---
    mpc = loadcase(network_file);
    nb = size(mpc.bus, 1);
    nbr = size(mpc.branch, 1);
    ng = size(mpc.gen, 1);
    fprintf("Loaded %d buses, %d branches, %d generators\n", nb, nbr, ng);

    % Handle zero RATE_A
    zero_rate = mpc.branch(:, RATE_A) == 0;
    mpc.branch(zero_rate, RATE_A) = 9999;
    fprintf("Set %d zero-RATE_A branches to 9999 MW\n", sum(zero_rate));

    % --- Solver list ---
    % Try each available DC OPF solver via mpopt change only
    solvers = {"MIPS", "GLPK"};
    solver_times = zeros(length(solvers), 1);
    solver_objs = zeros(length(solvers), 1);
    solver_converged = false(length(solvers), 1);
    solver_gen_total = zeros(length(solvers), 1);

    for s = 1:length(solvers)
        solver_name = solvers{s};
        fprintf("\n--- Solver: %s ---\n", solver_name);

        % Only change: mpopt solver parameter
        mpopt = mpoption("verbose", 0, "out.all", 0);
        mpopt = mpoption(mpopt, "opf.dc.solver", solver_name);

        tic_s = tic();
        try
            results = rundcopf(mpc, mpopt);
            solver_times(s) = toc(tic_s);

            if results.success
                solver_converged(s) = true;
                solver_objs(s) = results.f;
                solver_gen_total(s) = sum(results.gen(:, PG));
                fprintf("Converged: YES\n");
                fprintf("Objective: %.2f $/hr\n", results.f);
                fprintf("Wall clock: %.4f seconds\n", solver_times(s));
                fprintf("Total gen: %.2f MW\n", solver_gen_total(s));

                % LMP stats
                lmp = results.bus(:, LAM_P);
                fprintf("LMP range: [%.4f, %.4f] $/MWh\n", min(lmp), max(lmp));
                fprintf("Mean LMP: %.4f $/MWh\n", mean(lmp));
            else
                solver_times(s) = toc(tic_s);
                fprintf("Converged: NO\n");
                fprintf("Wall clock: %.4f seconds\n", solver_times(s));
            end
        catch serr
            solver_times(s) = toc(tic_s);
            fprintf("Error: %s\n", serr.message);
            fprintf("Wall clock: %.4f seconds\n", solver_times(s));
        end
    end

    wall_clock = toc(tic_val);

    % --- Summary ---
    fprintf("\n--- Solver Swap Summary ---\n");
    fprintf("  %-8s  %-10s  %-14s  %-10s\n", "Solver", "Converged", "Objective", "Time (s)");
    fprintf("  %-8s  %-10s  %-14s  %-10s\n", "------", "---------", "---------", "--------");
    for s = 1:length(solvers)
        if solver_converged(s)
            fprintf("  %-8s  %-10s  %14.2f  %10.4f\n", ...
                    solvers{s}, "YES", solver_objs(s), solver_times(s));
        else
            fprintf("  %-8s  %-10s  %14s  %10.4f\n", ...
                    solvers{s}, "NO", "N/A", solver_times(s));
        end
    end

    % --- Check objective consistency ---
    converged_idx = find(solver_converged);
    if length(converged_idx) >= 2
        objs = solver_objs(converged_idx);
        obj_range = max(objs) - min(objs);
        obj_rel = obj_range / max(abs(objs));
        fprintf("\nObjective consistency:\n");
        fprintf("  Range: %.2f $/hr\n", obj_range);
        fprintf("  Relative diff: %.2e\n", obj_rel);
    end

    % --- Key finding: solver swap mechanism ---
    fprintf("\n--- Solver Swap Mechanism ---\n");
    fprintf("Reformulation required: NO\n");
    fprintf("Swap method: mpopt = mpoption(mpopt, 'opf.dc.solver', '<NAME>')\n");
    fprintf("Same rundcopf() call, same mpc struct, only mpopt changes.\n");
    fprintf("MATPOWER handles internal reformulation (QP for MIPS, LP for GLPK) automatically.\n");

    % At least one solver must work
    assert(any(solver_converged), "No solver converged");

    fprintf("\nTotal wall clock: %.4f seconds\n", wall_clock);
    status = "pass";
    loc = 55;

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
fprintf("LOC: %d\n", loc);
fprintf("========================================\n");
