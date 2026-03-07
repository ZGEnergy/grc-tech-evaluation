%% Test B-1: Custom Constraints (Flow Gate Limit + Dual Values) on IEEE 39-bus (TINY)
%%
%% Pass condition: Add a flow gate limit (sum of flows on a specified set of
%% lines <= threshold) to DC OPF. Read and assert on the custom constraint's
%% dual value (non-zero when binding, zero when not). Produce a binding
%% constraint report.
%%
%% Approach: Use toggle_iflims (built-in interface flow limit extension) which
%% registers userfcn callbacks to add linear constraints on aggregate branch
%% flows. Dual values are returned in results.if.mu.u and results.if.mu.l.
%%
%% Usage (from evaluations/matpower/):
%%   octave tests/extensibility/test_b1_custom_constraints_tiny.m

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
fprintf("TEST B-1: Custom Constraints (Flow Gate) on TINY (IEEE 39-bus)\n");
fprintf("========================================\n");

status = "fail";
wall_clock = 0;
loc = 0;

tic_val = tic();
try
    % --- Load case ---
    mpc = loadcase(network_file);
    fprintf("Loaded %d buses, %d branches, %d generators\n", ...
            size(mpc.bus, 1), size(mpc.branch, 1), size(mpc.gen, 1));

    % --- First, set RATE_A on all branches so base OPF has meaningful flows ---
    % case39 has zero RATE_A; set generous limits so base case is unconstrained
    mpc.branch(:, RATE_A) = 9999;

    mpopt = mpoption("verbose", 0, "out.all", 0);

    % --- Baseline: DC OPF without interface flow limits ---
    fprintf("\n--- Baseline DC OPF (no flow gate) ---\n");
    results_base = rundcopf(mpc, mpopt);
    assert(results_base.success == 1, "Baseline DC OPF did not converge");
    fprintf("Baseline objective: %.2f $/hr\n", results_base.f);

    % --- Define flow gate (interface) ---
    % Create an interface across lines connecting gen-heavy area to load area.
    % Interface 1: branches 3 (bus 2->25), 9 (bus 5->6), 14 (bus 9->39)
    % These are chosen as a corridor between the generation and load areas.
    %
    % Interface 2: branches 1 (bus 1->2), 2 (bus 1->39) — for non-binding test

    % Identify branch indices by from/to buses
    br_from = mpc.branch(:, F_BUS);
    br_to   = mpc.branch(:, T_BUS);

    % Find specific branches for interface 1
    br3  = find(br_from == 2  & br_to == 25);
    br9  = find(br_from == 5  & br_to == 6);
    br14 = find(br_from == 9  & br_to == 39);

    if isempty(br3) || isempty(br9) || isempty(br14)
        % Fall back: use first 3 branches
        fprintf("  WARN: Could not find expected branches, using first 3\n");
        br3 = 1;
        br9 = 2;
        br14 = 3;
    end

    fprintf("Interface 1 branches: %d (%d->%d), %d (%d->%d), %d (%d->%d)\n", ...
            br3, br_from(br3), br_to(br3), ...
            br9, br_from(br9), br_to(br9), ...
            br14, br_from(br14), br_to(br14));

    % Get baseline flows on these branches to set a tight limit
    flow_br3  = results_base.branch(br3, PF);
    flow_br9  = results_base.branch(br9, PF);
    flow_br14 = results_base.branch(br14, PF);
    baseline_iface_flow = flow_br3 + flow_br9 + flow_br14;
    fprintf("Baseline interface 1 flow: %.2f + %.2f + %.2f = %.2f MW\n", ...
            flow_br3, flow_br9, flow_br14, baseline_iface_flow);

    % Set threshold to 80% of baseline flow (should be binding)
    binding_threshold = 0.8 * abs(baseline_iface_flow);
    % Set a very loose threshold for non-binding interface
    nonbinding_threshold = 9999;

    fprintf("Binding threshold (80%% of baseline): %.2f MW\n", binding_threshold);

    % --- Configure interface flow limits ---
    % mpc.if.map: [interface_id, signed_branch_idx]
    %   Positive branch idx = same direction as interface
    %   Negative branch idx = opposite direction
    mpc.if.map = [
                  1,  br3
                  1,  br9
                  1,  br14
                  2,  1     % Interface 2: just branch 1
                  2,  2     % Interface 2: branch 2
                 ];

    % mpc.if.lims: [interface_id, lower_limit, upper_limit]
    mpc.if.lims = [
                   1, -binding_threshold, binding_threshold
                   2, -nonbinding_threshold, nonbinding_threshold
                  ];

    % Enable interface flow limits
    mpc = toggle_iflims(mpc, "on");

    % --- Solve DC OPF with flow gate ---
    fprintf("\n--- DC OPF with flow gate constraints ---\n");
    results = rundcopf(mpc, mpopt);
    assert(results.success == 1, "DC OPF with flow gate did not converge");
    fprintf("Constrained objective: %.2f $/hr\n", results.f);
    fprintf("Objective increase: %.2f $/hr (%.2f%%)\n", ...
            results.f - results_base.f, ...
            100 * (results.f - results_base.f) / results_base.f);

    wall_clock = toc(tic_val);

    % --- Extract interface flow results and dual values ---
    assert(isfield(results, "if"), "results.if field not found");

    iface_flow = results.if.P;
    mu_lower   = results.if.mu.l;
    mu_upper   = results.if.mu.u;

    fprintf("\n--- Interface Flow Results ---\n");
    fprintf("  Interface  Flow(MW)   Lower_Lim  Upper_Lim  mu_lower   mu_upper   Binding?\n");

    n_iface = length(iface_flow);
    binding_status = cell(n_iface, 1);
    for i = 1:n_iface
        is_binding = (mu_lower(i) > 1e-6) || (mu_upper(i) > 1e-6);
        if is_binding
            binding_status{i} = "YES";
        else
            binding_status{i} = "NO";
        end
        lim_l = mpc.if.lims(i, 2);
        lim_u = mpc.if.lims(i, 3);
        fprintf("  %4d      %8.2f   %8.2f   %8.2f   %8.4f   %8.4f   %s\n", ...
                i, iface_flow(i), lim_l, lim_u, mu_lower(i), mu_upper(i), binding_status{i});
    end

    % --- Assertions ---
    % Interface 1 should be binding (tight threshold)
    iface1_binding = (mu_lower(1) > 1e-6) || (mu_upper(1) > 1e-6);
    fprintf("\nInterface 1 (tight threshold) binding: %s\n", mat2str(iface1_binding));
    fprintf("  Dual value (mu_upper): %.6f $/MW\n", mu_upper(1));
    fprintf("  Dual value (mu_lower): %.6f $/MW\n", mu_lower(1));

    % Interface 2 should NOT be binding (loose threshold)
    iface2_binding = (mu_lower(2) > 1e-6) || (mu_upper(2) > 1e-6);
    fprintf("Interface 2 (loose threshold) binding: %s\n", mat2str(iface2_binding));
    fprintf("  Dual value (mu_upper): %.6f $/MW\n", mu_upper(2));
    fprintf("  Dual value (mu_lower): %.6f $/MW\n", mu_lower(2));

    assert(iface1_binding, ...
           "Interface 1 should be binding with tight threshold");
    assert(~iface2_binding, ...
           "Interface 2 should NOT be binding with loose threshold");
    assert(results.f >= results_base.f - 1e-6, ...
           "Constrained objective should be >= unconstrained objective");

    % --- Binding constraint report ---
    fprintf("\n--- BINDING CONSTRAINT REPORT ---\n");
    fprintf("Total interfaces: %d\n", n_iface);
    n_binding = sum(mu_lower > 1e-6) + sum(mu_upper > 1e-6);
    fprintf("Binding interfaces: %d\n", n_binding);
    for i = 1:n_iface
        if mu_upper(i) > 1e-6
            fprintf("  Interface %d: BINDING at upper limit (%.2f MW), dual=%.4f $/MW\n", ...
                    i, mpc.if.lims(i, 3), mu_upper(i));
        elseif mu_lower(i) > 1e-6
            fprintf("  Interface %d: BINDING at lower limit (%.2f MW), dual=%.4f $/MW\n", ...
                    i, mpc.if.lims(i, 2), mu_lower(i));
        else
            fprintf("  Interface %d: not binding (flow=%.2f MW, limits=[%.2f, %.2f])\n", ...
                    i, iface_flow(i), mpc.if.lims(i, 2), mpc.if.lims(i, 3));
        end
    end

    % --- Also check LMP differentiation ---
    lam_p = results.bus(:, LAM_P);
    fprintf("\nLMP range: [%.4f, %.4f] $/MWh (spread: %.4f)\n", ...
            min(lam_p), max(lam_p), max(lam_p) - min(lam_p));
    lam_base = results_base.bus(:, LAM_P);
    fprintf("Baseline LMP range: [%.4f, %.4f] $/MWh (spread: %.4f)\n", ...
            min(lam_base), max(lam_base), max(lam_base) - min(lam_base));

    if max(lam_p) - min(lam_p) > 1e-4
        fprintf("Flow gate created LMP differentiation: YES\n");
    else
        fprintf("Flow gate created LMP differentiation: NO (uniform LMPs persist)\n");
    end

    fprintf("\nAll assertions passed.\n");
    status = "pass";
    loc = 95;

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
