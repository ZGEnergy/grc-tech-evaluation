% Gate tests for MATPOWER evaluation: G-1 (TINY), G-2 (SMALL), G-3 (MEDIUM)
% Loads each network, verifies bus/branch/gen counts, and runs data quality audits.
%
% Usage (from evaluations/matpower/):
%   octave tests/test_gate.m
%
% Note: uses double-quoted strings for Octave compatibility when sourced.

% Add MATPOWER to path
mp_root = fullfile(pwd, "matpower8.1");
addpath(fullfile(mp_root, "lib"));
addpath(fullfile(mp_root, "data"));
addpath(fullfile(mp_root, "mips", "lib"));
addpath(fullfile(mp_root, "mp-opt-model", "lib"));
addpath(fullfile(mp_root, "mptest", "lib"));

data_dir = fullfile(pwd, "..", "..", "data", "networks");

% Reference counts: [buses, branches, gens]
% G-1 TINY: IEEE 39-bus (known reference)
% G-2 SMALL: ACTIVSg 2000 (discovered: 2000/3206/544)
% G-3 MEDIUM: ACTIVSg 10000 (discovered: 10000/12706/2485)
test_ids     = {"G-1", "G-2", "G-3"};
slugs        = {"ingest_tiny", "ingest_small", "ingest_medium"};
tiers        = {"TINY", "SMALL", "MEDIUM"};
filenames    = {"case39.m", "case_ACTIVSg2000.m", "case_ACTIVSg10k.m"};
exp_buses    = [39, 2000, 10000];
exp_branches = [46, 3206, 12706];
exp_gens     = [10, 544, 2485];

all_pass = 1;
scale_cap = "MEDIUM";

for i = 1:3
    test_id  = test_ids{i};
    slug     = slugs{i};
    tier     = tiers{i};
    filename = filenames{i};

    filepath = fullfile(data_dir, filename);
    fprintf("\n========================================\n");
    fprintf("TEST %s (%s): %s\n", test_id, tier, filename);
    fprintf("========================================\n");

    tic_val = tic();
    try
        mpc = loadcase(filepath);
        load_time = toc(tic_val);
    catch err
        load_time = toc(tic_val);
        fprintf("FAIL: Could not load case file: %s\n", err.message);
        fprintf("LOAD_TIME: %.4f\n", load_time);
        fprintf("STATUS: FAIL\n");
        all_pass = 0;
        if strcmp(test_id, "G-1")
            scale_cap = "NONE";
            fprintf("\nHALT: G-1 failed. Tool disqualified.\n");
            fprintf("SCALE_CAP: %s\n", scale_cap);
            exit(1);
        elseif strcmp(test_id, "G-2")
            scale_cap = "TINY";
        elseif strcmp(test_id, "G-3")
            scale_cap = "SMALL";
        end
        continue
    end

    actual_buses = size(mpc.bus, 1);
    actual_branches = size(mpc.branch, 1);
    actual_gens = size(mpc.gen, 1);

    fprintf("Buses:    %d\n", actual_buses);
    fprintf("Branches: %d\n", actual_branches);
    fprintf("Gens:     %d\n", actual_gens);
    fprintf("LOAD_TIME: %.4f\n", load_time);

    % Verify counts against reference
    if actual_buses ~= exp_buses(i) || actual_branches ~= exp_branches(i) || actual_gens ~= exp_gens(i)
        fprintf("FAIL: Count mismatch. Expected %d/%d/%d, got %d/%d/%d\n", ...
                exp_buses(i), exp_branches(i), exp_gens(i), actual_buses, actual_branches, actual_gens);
        fprintf("STATUS: FAIL\n");
        all_pass = 0;
        if strcmp(test_id, "G-1")
            scale_cap = "NONE";
            fprintf("\nHALT: G-1 failed. Tool disqualified.\n");
            fprintf("SCALE_CAP: %s\n", scale_cap);
            exit(1);
        elseif strcmp(test_id, "G-2")
            scale_cap = "TINY";
        elseif strcmp(test_id, "G-3")
            scale_cap = "SMALL";
        end
        continue
    else
        fprintf("Count check: PASS (matches reference %d/%d/%d)\n", ...
                exp_buses(i), exp_branches(i), exp_gens(i));
    end

    % ---- Post-import data quality audit ----
    n_issues = 0;

    % 1. Bus voltages
    bus_vm = mpc.bus(:, 8);
    bus_va = mpc.bus(:, 9);
    if any(isnan(bus_vm)) || any(isinf(bus_vm))
        fprintf("  WARN: NaN/Inf in bus voltage magnitudes (Vm)\n");
        n_issues = n_issues + 1;
    end
    if any(isnan(bus_va)) || any(isinf(bus_va))
        fprintf("  WARN: NaN/Inf in bus voltage angles (Va)\n");
        n_issues = n_issues + 1;
    end

    % 2. Branch flow limits (RATE_A, col 6)
    rate_a = mpc.branch(:, 6);
    n_zero_rate = sum(rate_a == 0);
    if any(isnan(rate_a)) || any(isinf(rate_a))
        fprintf("  WARN: NaN/Inf in branch RATE_A\n");
        n_issues = n_issues + 1;
    end
    if n_zero_rate > 0
        fprintf("  WARN: %d/%d branches have zero RATE_A (unlimited flow)\n", n_zero_rate, actual_branches);
        n_issues = n_issues + 1;
    end

    % 3. Generator limits
    gen_pmax = mpc.gen(:, 9);
    gen_pmin = mpc.gen(:, 10);
    gen_qmax = mpc.gen(:, 4);
    gen_qmin = mpc.gen(:, 5);
    if any(isnan(gen_pmax)) || any(isinf(gen_pmax))
        fprintf("  WARN: NaN/Inf in generator PMAX\n");
        n_issues = n_issues + 1;
    end
    if any(isnan(gen_pmin)) || any(isinf(gen_pmin))
        fprintf("  WARN: NaN/Inf in generator PMIN\n");
        n_issues = n_issues + 1;
    end
    if any(isnan(gen_qmax)) || any(isinf(gen_qmax))
        fprintf("  WARN: NaN/Inf in generator QMAX\n");
        n_issues = n_issues + 1;
    end
    if any(isnan(gen_qmin)) || any(isinf(gen_qmin))
        fprintf("  WARN: NaN/Inf in generator QMIN\n");
        n_issues = n_issues + 1;
    end

    % 4. Generator cost data
    if isfield(mpc, "gencost")
        gencost = mpc.gencost;
        if any(any(isnan(gencost))) || any(any(isinf(gencost)))
            fprintf("  WARN: NaN/Inf in generator cost data\n");
            n_issues = n_issues + 1;
        end
        fprintf("Gencost rows: %d\n", size(gencost, 1));
    else
        fprintf("  WARN: No gencost field (OPF will fail)\n");
        n_issues = n_issues + 1;
    end

    % 5. Slack/reference bus (type == 3)
    ref_buses = find(mpc.bus(:, 2) == 3);
    if isempty(ref_buses)
        fprintf("  WARN: No reference/slack bus found (bus type 3)\n");
        n_issues = n_issues + 1;
    else
        fprintf("Reference bus(es):");
        for rb = 1:length(ref_buses)
            fprintf(" %d", mpc.bus(ref_buses(rb), 1));
        end
        fprintf("\n");
    end

    if n_issues == 0
        fprintf("Data quality audit: PASS (no issues)\n");
    else
        fprintf("Data quality audit: %d warning(s)\n", n_issues);
    end

    fprintf("STATUS: PASS\n");
end

fprintf("\n========================================\n");
fprintf("SCALE_CAP: %s\n", scale_cap);
fprintf("ALL_PASS: %d\n", all_pass);
fprintf("========================================\n");
