% Gate tests for MATPOWER evaluation
% Tests G-1 (TINY), G-2 (SMALL), G-3 (MEDIUM)
%
% Usage: cd evaluations/matpower && octave --no-gui tests/gate_tests.m

% Add MATPOWER to path
mp_root = fullfile(pwd, 'matpower8.1');
addpath(fullfile(mp_root, 'lib'));
addpath(fullfile(mp_root, 'data'));
addpath(fullfile(mp_root, 'mips', 'lib'));
addpath(fullfile(mp_root, 'mp-opt-model', 'lib'));
addpath(fullfile(mp_root, 'mptest', 'lib'));

data_dir = fullfile('..', '..', 'data', 'networks');

% Reference values
test_ids  = {'G-1', 'G-2', 'G-3'};
files     = {'case39.m', 'case_ACTIVSg2000.m', 'case_ACTIVSg10k.m'};
exp_buses = [39, 2000, 10000];
exp_brs   = [46, 3206, 12706];
exp_gens  = [10, 544, 2485];
tiers     = {'TINY', 'SMALL', 'MEDIUM'};

all_pass = true;

for i = 1:3
    fprintf('\n========================================\n');
    fprintf('Test %s: %s (%s)\n', test_ids{i}, files{i}, tiers{i});
    fprintf('========================================\n');

    fpath = fullfile(data_dir, files{i});
    try
        tic;
        mpc = loadcase(fpath);
        load_time = toc;
        fprintf('  Load time: %.3f s\n', load_time);
    catch e
        fprintf('  FAIL: loadcase error: %s\n', e.message);
        all_pass = false;
        if i == 1
            fprintf('\n  TINY gate failed -- halting. scale_cap: NONE\n');
        end
        continue
    end

    nbus = size(mpc.bus, 1);
    nbr  = size(mpc.branch, 1);
    ngen = size(mpc.gen, 1);

    bus_ok = (nbus == exp_buses(i));
    br_ok  = (nbr == exp_brs(i));
    gen_ok = (ngen == exp_gens(i));

    if bus_ok
        bs = 'OK';
    else
        bs = 'MISMATCH';
    end
    if br_ok
        brs = 'OK';
    else
        brs = 'MISMATCH';
    end
    if gen_ok
        gs = 'OK';
    else
        gs = 'MISMATCH';
    end

    fprintf('  Buses:      %d (expected %d) %s\n', nbus, exp_buses(i), bs);
    fprintf('  Branches:   %d (expected %d) %s\n', nbr, exp_brs(i), brs);
    fprintf('  Generators: %d (expected %d) %s\n', ngen, exp_gens(i), gs);

    count_ok = bus_ok && br_ok && gen_ok;

    % --- Post-import audit ---
    fprintf('\n  --- Post-import audit ---\n');

    % NaN checks
    nan_bus = sum(sum(isnan(mpc.bus)));
    nan_br  = sum(sum(isnan(mpc.branch)));
    nan_gen = sum(sum(isnan(mpc.gen)));
    fprintf('  NaN in bus:    %d\n', nan_bus);
    fprintf('  NaN in branch: %d\n', nan_br);
    fprintf('  NaN in gen:    %d\n', nan_gen);

    % Cost data
    has_gencost = isfield(mpc, 'gencost');
    if has_gencost
        ngencost = size(mpc.gencost, 1);
        if ngencost >= ngen
            cs = 'OK';
        else
            cs = 'MISMATCH';
        end
        fprintf('  gencost rows:  %d (gen rows: %d) %s\n', ngencost, ngen, cs);
        nan_cost = sum(sum(isnan(mpc.gencost)));
        fprintf('  NaN in gencost: %d\n', nan_cost);
    else
        fprintf('  gencost: NOT PRESENT\n');
    end

    % Flow limits (RATE_A is column 6 of branch)
    rate_a = mpc.branch(:, 6);
    n_zero_rate = sum(rate_a == 0);
    n_nonzero_rate = sum(rate_a > 0);
    fprintf('  Branch flow limits: %d nonzero, %d zero (of %d)\n', ...
            n_nonzero_rate, n_zero_rate, nbr);

    % Slack bus (bus_type == 3 is ref/slack)
    slack_buses = find(mpc.bus(:, 2) == 3);
    fprintf('  Slack bus(es): %d found (bus IDs: %s)\n', ...
            length(slack_buses), mat2str(mpc.bus(slack_buses, 1)'));

    % Overall pass/fail
    audit_ok = (nan_bus == 0) && (nan_br == 0) && (nan_gen == 0) && ...
               (length(slack_buses) >= 1);
    pass = count_ok && audit_ok;

    if pass
        fprintf('\n  RESULT: PASS\n');
    else
        fprintf('\n  RESULT: FAIL\n');
        all_pass = false;
        if i == 1
            fprintf('\n  TINY gate failed -- halting. scale_cap: NONE\n');
        end
    end
end

if all_pass
    fprintf('\n\nAll gate tests PASSED. scale_cap: MEDIUM\n');
else
    fprintf('\n\nSome gate tests failed.\n');
end
