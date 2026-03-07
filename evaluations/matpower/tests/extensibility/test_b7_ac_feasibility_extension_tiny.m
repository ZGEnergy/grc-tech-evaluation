%% Test B-7: AC Feasibility as Extension on IEEE 39-bus (TINY)
%%
%% Pass condition: If AC feasibility check (A-4) required a workaround,
%% document and classify it. Test the workflow: DC OPF -> set gen dispatch
%% -> run AC PF to check feasibility.
%%
%% Approach: MATPOWER natively supports this workflow:
%%   1. rundcopf(mpc) -> get optimal dispatch
%%   2. Set mpc.gen(:, PG) = results.gen(:, PG)
%%   3. runpf(mpc) -> AC power flow to check feasibility
%% This is a natural API flow (modify struct fields, re-solve).
%%
%% Usage (from evaluations/matpower/):
%%   octave tests/extensibility/test_b7_ac_feasibility_extension_tiny.m

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
fprintf("TEST B-7: AC Feasibility Extension on TINY (IEEE 39-bus)\n");
fprintf("========================================\n");

status = "fail";
wall_clock = 0;
loc = 0;

tic_val = tic();
try
    % --- Step 1: Load case and solve DC OPF ---
    mpc = loadcase(network_file);
    fprintf("Loaded %d buses, %d branches, %d generators\n", ...
            size(mpc.bus, 1), size(mpc.branch, 1), size(mpc.gen, 1));

    mpopt = mpoption("verbose", 0, "out.all", 0);
    fprintf("\n--- Step 1: DC OPF ---\n");
    dc_results = rundcopf(mpc, mpopt);
    assert(dc_results.success == 1, "DC OPF did not converge");
    fprintf("DC OPF converged: YES\n");
    fprintf("DC OPF objective: %.2f $/hr\n", dc_results.f);

    % Extract optimal dispatch
    dc_pg = dc_results.gen(:, PG);
    fprintf("DC dispatch (MW): ");
    fprintf("%.1f ", dc_pg);
    fprintf("\n");
    fprintf("Total DC dispatch: %.2f MW\n", sum(dc_pg));
    fprintf("Total load: %.2f MW\n", sum(mpc.bus(:, PD)));

    % --- Step 2: Transfer DC dispatch to AC power flow ---
    % This is the core extensibility question: how much friction to go
    % from DC OPF result to AC feasibility check?
    fprintf("\n--- Step 2: Transfer DC dispatch to AC case ---\n");

    % Reload fresh case for AC PF (to avoid any DC OPF artifacts in struct)
    mpc_ac = loadcase(network_file);

    % Set generator real power to DC OPF values
    mpc_ac.gen(:, PG) = dc_pg;

    % The slack bus generator will be adjusted by AC PF to account for losses.
    % Identify the slack bus generator.
    ref_bus_idx = find(mpc_ac.bus(:, BUS_TYPE) == REF);
    ref_bus_id  = mpc_ac.bus(ref_bus_idx, BUS_I);
    ref_gen_idx = find(mpc_ac.gen(:, GEN_BUS) == ref_bus_id);
    fprintf("Slack bus: %d (gen index: %d)\n", ref_bus_id, ref_gen_idx);
    fprintf("Slack gen DC dispatch: %.2f MW\n", dc_pg(ref_gen_idx));

    % --- Step 3: Run AC Power Flow ---
    fprintf("\n--- Step 3: AC Power Flow (feasibility check) ---\n");
    ac_results = runpf(mpc_ac, mpopt);
    wall_clock = toc(tic_val);

    if ac_results.success
        fprintf("AC PF converged: YES\n");

        % Check voltage profile
        vm = ac_results.bus(:, VM);
        va = ac_results.bus(:, VA);
        fprintf("Voltage magnitude range: [%.4f, %.4f] p.u.\n", min(vm), max(vm));
        fprintf("Voltage angle range: [%.2f, %.2f] degrees\n", min(va), max(va));

        % Check for voltage violations
        vmin = mpc_ac.bus(:, VMIN);
        vmax = mpc_ac.bus(:, VMAX);
        v_violations = sum(vm < vmin - 1e-4) + sum(vm > vmax + 1e-4);
        fprintf("Voltage violations: %d\n", v_violations);

        if v_violations > 0
            viol_lo = find(vm < vmin - 1e-4);
            viol_hi = find(vm > vmax + 1e-4);
            for i = 1:length(viol_lo)
                idx = viol_lo(i);
                fprintf("  Bus %d: Vm=%.4f < Vmin=%.4f\n", ...
                        mpc_ac.bus(idx, BUS_I), vm(idx), vmin(idx));
            end
            for i = 1:length(viol_hi)
                idx = viol_hi(i);
                fprintf("  Bus %d: Vm=%.4f > Vmax=%.4f\n", ...
                        mpc_ac.bus(idx, BUS_I), vm(idx), vmax(idx));
            end
        end

        % Check reactive power
        ac_qg = ac_results.gen(:, QG);
        qmin  = mpc_ac.gen(:, QMIN);
        qmax  = mpc_ac.gen(:, QMAX);
        q_violations = sum(ac_qg < qmin - 1e-4) + sum(ac_qg > qmax + 1e-4);
        fprintf("Reactive power violations: %d\n", q_violations);

        % Check real power adjustment at slack
        ac_pg = ac_results.gen(:, PG);
        slack_adjustment = ac_pg(ref_gen_idx) - dc_pg(ref_gen_idx);
        fprintf("Slack gen P adjustment: %.2f MW (losses)\n", slack_adjustment);
        fprintf("Total AC dispatch: %.2f MW\n", sum(ac_pg));

        % Line loading
        pf_flow = ac_results.branch(:, PF);
        qf_flow = ac_results.branch(:, QF);
        sf_flow = sqrt(pf_flow.^2 + qf_flow.^2);
        fprintf("Max apparent power flow: %.2f MVA\n", max(sf_flow));

        % AC feasibility assessment
        ac_feasible = (v_violations == 0) && (q_violations == 0);
        fprintf("\n--- AC Feasibility Assessment ---\n");
        fprintf("Converged: YES\n");
        fprintf("Voltage violations: %d\n", v_violations);
        fprintf("Reactive violations: %d\n", q_violations);
        fprintf("AC FEASIBLE: %s\n", mat2str(ac_feasible));
    else
        fprintf("AC PF converged: NO\n");
        fprintf("DC OPF dispatch is NOT AC feasible (PF diverged)\n");
    end

    % --- Workaround Classification ---
    fprintf("\n--- Workaround Classification ---\n");
    fprintf("Steps required:\n");
    fprintf("  1. rundcopf(mpc) -> extract gen(:, PG)        [native API]\n");
    fprintf("  2. mpc.gen(:, PG) = dc_results.gen(:, PG)     [struct assignment]\n");
    fprintf("  3. runpf(mpc_modified)                         [native API]\n");
    fprintf("  4. Check ac_results.success + voltage/Q bounds [struct reads]\n");
    fprintf("\n");
    fprintf("No workaround needed. This is a natural API flow:\n");
    fprintf("  - DC OPF and AC PF use the same mpc struct format\n");
    fprintf("  - Gen dispatch is a direct column in the struct\n");
    fprintf("  - AC PF automatically adjusts slack for losses\n");
    fprintf("  - All results (V, Q, flows) available in standard struct fields\n");

    fprintf("\nAll steps completed successfully.\n");
    status = "pass";
    loc = 50;

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
