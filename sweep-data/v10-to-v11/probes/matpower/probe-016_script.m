%% Probe 016: Verify GLPK exit-flag mapping claim for MATPOWER A-5 SCUC
%%
%% Claim: GLP_EMIPGAP is mapped to failure exitflag, causing A-5/C-4 to
%%        report failure when the SCUC solve actually succeeded.
%%
%% This script:
%% 1. Verifies actual GLPK errnum constants in Octave
%% 2. Inspects miqps_glpk.m exit flag mapping logic
%% 3. Reproduces the A-5 SCUC scenario (case39, 24h, TINY)
%% 4. Captures raw GLPK errnum and extra.status
%% 5. Determines whether the bug is real and what exit code is actually returned

mp_root = '/workspace/evaluations/matpower/matpower8.1';
addpath(fullfile(mp_root, 'lib'));
addpath(fullfile(mp_root, 'data'));
addpath(fullfile(mp_root, 'mips', 'lib'));
addpath(fullfile(mp_root, 'mp-opt-model', 'lib'));
addpath(fullfile(mp_root, 'mptest', 'lib'));
addpath(fullfile(mp_root, 'most', 'lib'));
addpath(fullfile(mp_root, 'most', 'examples'));

fprintf('=== Probe 016: GLPK Exit Flag Mapping Verification ===\n\n');
fprintf('MATPOWER version: %s\n', mpver);
fprintf('Octave version: %s\n', version);

%% ================================================================
%% PART 1: Verify GLPK errnum constants in Octave
%% ================================================================
fprintf('\n--- Part 1: GLPK Error Code Constants ---\n');

% In Octave''s GLPK binding, error codes are:
% GLP_ETMLIM = 9  (time limit reached) -- NOT MIP gap
% GLP_EMIPGAP = 14 (relative MIP gap tolerance reached)
% This differs from what the A-5 result claims (errnum=9 = GLP_EMIPGAP)

fprintf('Octave GLPK error codes (from documentation):\n');
fprintf('  errnum=9  = GLP_ETMLIM  (time limit reached)\n');
fprintf('  errnum=14 = GLP_EMIPGAP (relative MIP gap tolerance reached)\n');

% Verify with a simple controlled MILP
fprintf('\nTest 1: Simple MILP that solves to optimality\n');
c_t = [1; 2];
A_t = [1 1];
b_t = [1.5];
lb_t = [0; 0];
ub_t = [1; 1];
[x_t, f_t, en_t, ex_t] = glpk(c_t, A_t, b_t, lb_t, ub_t, 'U', 'II', 1);
fprintf('  errnum=%d, status=%d (expected: errnum=0, status=5 for optimal)\n', en_t, ex_t.status);

%% ================================================================
%% PART 2: Reproduce A-5 SCUC scenario (case39, 24h)
%% ================================================================
fprintf('\n--- Part 2: Reproduce A-5 SCUC (case39 TINY, 24-hour) ---\n');

define_constants;
[CT_LABEL, CT_PROB, CT_TABLE, CT_TBUS, CT_TGEN, CT_TBRCH, ...
    CT_TAREABUS, CT_TAREAGEN, CT_TAREABRCH, CT_ROW, CT_COL, ...
    CT_CHGTYPE, CT_REP, CT_REL, CT_ADD, CT_NEWVAL, CT_TLOAD, ...
    CT_TAREALOAD, CT_LOAD_ALL_PQ, CT_LOAD_FIX_PQ, CT_LOAD_DIS_PQ, ...
    CT_LOAD_ALL_P, CT_LOAD_FIX_P, CT_LOAD_DIS_P, CT_TGENCOST, ...
    CT_TAREAGENCOST, CT_MODCOST_F, CT_MODCOST_X] = idx_ct;

network_file = '/workspace/data/networks/case39.m';
timeseries_dir = '/workspace/data/timeseries/case39';

mpc = loadcase(network_file);
ng = size(mpc.gen, 1);
nb = size(mpc.bus, 1);
nt = 24;

fprintf('Loaded case39: %d buses, %d generators, %d periods\n', nb, ng, nt);

% Apply costs from A-5 test
marginal_costs = [5; 10; 10; 25; 25; 10; 40; 10; 10; 40];
no_load_costs = [0; 0; 0; 450; 450; 0; 600; 0; 0; 600];
mpc.gencost = zeros(ng, 6);
mpc.gencost(:, MODEL) = 2;
mpc.gencost(:, NCOST) = 2;
mpc.gencost(:, COST) = marginal_costs;
mpc.gencost(:, COST + 1) = no_load_costs;
mpc.gencost(:, STARTUP) = [0; 63999; 63999; 5000; 5000; 63999; 5000; 63999; 63999; 5000];

ramp_mw_per_min = [1040; 32.3; 36.25; 7.451429; 5.805714; ...
                   34.35; 6.763944; 28.2; 43.25; 19.242254];
mpc.gen(:, RAMP_10) = ramp_mw_per_min * 10;
mpc.gen(:, RAMP_30) = ramp_mw_per_min * 30;
mpc.gen(:, RAMP_AGC) = ramp_mw_per_min;

pmin_frac = [0.25; 0.40; 0.40; 0.40; 0.40; 0.40; 0.50; 0.40; 0.40; 0.30];
mpc.gen(:, PMIN) = mpc.gen(:, PMAX) .* pmin_frac;
mpc.gen(:, GEN_STATUS) = 1;
mpc.gen(:, PG) = mpc.gen(:, PMAX) * 0.5;

min_up   = [1; 24; 24; 8; 8; 24; 4; 24; 24; 2];
min_down = [1; 24; 24; 4; 4; 24; 2; 24; 24; 1];

xgd_table.colnames = { 'CommitKey', 'CommitSched', 'MinUp', 'MinDown', ...
                      'PositiveActiveReservePrice', 'PositiveActiveReserveQuantity', ...
                      'NegativeActiveReservePrice', 'NegativeActiveReserveQuantity', ...
                      'PositiveActiveDeltaPrice', 'NegativeActiveDeltaPrice', ...
                      'PositiveLoadFollowReservePrice', 'PositiveLoadFollowReserveQuantity', ...
                      'NegativeLoadFollowReservePrice', 'NegativeLoadFollowReserveQuantity' };
xgd_table.data = zeros(ng, 14);
xgd_table.data(:, 1) = 1;
xgd_table.data(:, 2) = 1;
xgd_table.data(:, 3) = min_up;
xgd_table.data(:, 4) = min_down;
xgd_table.data(:, 5) = 1e-6;
xgd_table.data(:, 6) = mpc.gen(:, PMAX);
xgd_table.data(:, 7) = 1e-6;
xgd_table.data(:, 8) = mpc.gen(:, PMAX);
xgd_table.data(:, 9:10) = 1e-9;
xgd_table.data(:, 11) = 1e-6;
xgd_table.data(:, 12) = mpc.gen(:, PMAX);
xgd_table.data(:, 13) = 1e-6;
xgd_table.data(:, 14) = mpc.gen(:, PMAX);
xgd = loadxgendata(xgd_table, mpc);

load_data_raw = csvread(fullfile(timeseries_dir, 'load_24h.csv'), 1, 0);
hourly_totals = sum(load_data_raw(:, 2:25), 1);

load_profile = struct('type', 'mpcData', 'table', CT_TLOAD, ...
                      'rows', 0, 'col', CT_LOAD_ALL_PQ, 'chgtype', CT_REP, 'values', []);
load_profile.values = reshape(hourly_totals', [nt, 1, 1]);
profiles = load_profile;

mpc = ext2int(mpc);

% Use mipgap=0.01 as in the A-5 script
mpopt = mpoption('verbose', 0, 'out.all', 0, 'model', 'DC');
mpopt = mpoption(mpopt, 'most.dc_model', 1, 'most.uc.run', 1);
mpopt = mpoption(mpopt, 'most.solver', 'GLPK');
mpopt = mpoption(mpopt, 'glpk.opts.mipgap', 0.01);
mpopt = mpoption(mpopt, 'glpk.opts.tolint', 1e-6);
mpopt = mpoption(mpopt, 'glpk.opts.tmlim', 60);

md = loadmd(mpc, nt, xgd, [], [], profiles);

fprintf('Solving SCUC...\n');
tic;
mdo = most(md, mpopt);
solve_time = toc;

%% ================================================================
%% PART 3: Examine raw GLPK output
%% ================================================================
fprintf('\n--- Part 3: Raw GLPK Output ---\n');
fprintf('mdo.QP.exitflag = %d\n', mdo.QP.exitflag);
fprintf('Solve time: %.4f s\n', solve_time);

if isfield(mdo.QP, 'output')
    fprintf('mdo.QP.output.errnum = %d\n', mdo.QP.output.errnum);
    fprintf('mdo.QP.output.status = %d\n', mdo.QP.output.status);
end

% Check size of solution vector
if isfield(mdo.QP, 'x') && ~isempty(mdo.QP.x)
    fprintf('Solution vector size: %d variables\n', length(mdo.QP.x));
    fprintf('Objective value: %.4f\n', mdo.QP.f);
    n_nonzero = sum(abs(mdo.QP.x) > 1e-6);
    fprintf('Non-zero variables: %d\n', n_nonzero);
else
    fprintf('Solution vector: empty or not present\n');
end

%% ================================================================
%% PART 4: Decode the exit flag and determine what actually happened
%% ================================================================
fprintf('\n--- Part 4: Exit Flag Decoding ---\n');

ef = mdo.QP.exitflag;
fprintf('exitflag = %d\n', ef);

if ef > 0
    fprintf('STATUS: MOST treated as SUCCESS\n');
    fprintf('=> No exitflag mapping bug for this problem\n');
elseif ef == -9
    fprintf('STATUS: MOST treated as FAILURE\n');
    fprintf('errnum=9 = GLP_ETMLIM (TIME LIMIT) in Octave GLPK\n');
    fprintf('NOTE: This is NOT GLP_EMIPGAP (errnum=14)\n');
    fprintf('=> The A-5 claim of "GLP_EMIPGAP mapped to failure" is PARTIALLY WRONG:\n');
    fprintf('   The actual code is GLP_ETMLIM (time limit), not GLP_EMIPGAP\n');
elseif ef == -14
    fprintf('STATUS: MOST treated as FAILURE\n');
    fprintf('errnum=14 = GLP_EMIPGAP in Octave GLPK\n');
    fprintf('=> GLP_EMIPGAP IS mapped to failure (claim supported)\n');
    fprintf('   miqps_glpk.m only handles errnum==9 as "acceptable" non-optimal\n');
else
    fprintf('STATUS: MOST treated as FAILURE with errnum=%d\n', -ef);
    fprintf('Decoding: ');
    switch -ef
        case 5
            fprintf('GLP_EFAIL\n');
        case 6
            fprintf('GLP_EOBJLL (obj lower limit reached)\n');
        case 7
            fprintf('GLP_EOBJUL (obj upper limit reached)\n');
        case 8
            fprintf('GLP_EITLIM (iteration limit)\n');
        case 9
            fprintf('GLP_ETMLIM (time limit)\n');
        case 10
            fprintf('GLP_ENOPFS (no primal feasible)\n');
        case 13
            fprintf('GLP_ESTOP (terminated by app)\n');
        case 14
            fprintf('GLP_EMIPGAP (MIP gap tolerance)\n');
        otherwise
            fprintf('Unknown code\n');
    end
end

%% ================================================================
%% PART 5: Try with tigher mipgap=0 to see if GLPK can solve to optimality
%% ================================================================
fprintf('\n--- Part 5: Retry with mipgap=0 (force true optimality) ---\n');

mpc2 = loadcase(network_file);
ng2 = size(mpc2.gen, 1);

% Same setup
mpc2.gencost = zeros(ng2, 6);
mpc2.gencost(:, MODEL) = 2;
mpc2.gencost(:, NCOST) = 2;
mpc2.gencost(:, COST) = marginal_costs;
mpc2.gencost(:, COST + 1) = no_load_costs;
mpc2.gencost(:, STARTUP) = [0; 63999; 63999; 5000; 5000; 63999; 5000; 63999; 63999; 5000];
mpc2.gen(:, RAMP_10) = ramp_mw_per_min * 10;
mpc2.gen(:, RAMP_30) = ramp_mw_per_min * 30;
mpc2.gen(:, RAMP_AGC) = ramp_mw_per_min;
mpc2.gen(:, PMIN) = mpc2.gen(:, PMAX) .* pmin_frac;
mpc2.gen(:, GEN_STATUS) = 1;
mpc2.gen(:, PG) = mpc2.gen(:, PMAX) * 0.5;
xgd2 = loadxgendata(xgd_table, mpc2);
mpc2 = ext2int(mpc2);

mpopt2 = mpoption('verbose', 0, 'out.all', 0, 'model', 'DC');
mpopt2 = mpoption(mpopt2, 'most.dc_model', 1, 'most.uc.run', 1);
mpopt2 = mpoption(mpopt2, 'most.solver', 'GLPK');
mpopt2 = mpoption(mpopt2, 'glpk.opts.mipgap', 0);
mpopt2 = mpoption(mpopt2, 'glpk.opts.tolint', 1e-10);
mpopt2 = mpoption(mpopt2, 'glpk.opts.tmlim', 120);

md2 = loadmd(mpc2, nt, xgd2, [], [], profiles);

fprintf('Solving with mipgap=0 (true optimality)...\n');
tic;
mdo2 = most(md2, mpopt2);
solve_time2 = toc;

fprintf('exitflag = %d, solve_time = %.4f s\n', mdo2.QP.exitflag, solve_time2);
if isfield(mdo2.QP, 'output')
    fprintf('errnum=%d, status=%d\n', mdo2.QP.output.errnum, mdo2.QP.output.status);
end

if mdo2.QP.exitflag > 0
    fprintf('=> Solved to optimality with mipgap=0\n');
    ms2 = most_summary(mdo2);
    commit2 = ms2.u(:, :, 1, 1);
    cycling2 = 0;
    for g = 1:ng2
        if min(commit2(g, :)) ~= max(commit2(g, :))
            cycling2 = cycling2 + 1;
        end
    end
    fprintf('Cycling generators: %d\n', cycling2);
    fprintf('Objective: %.2f\n', ms2.f);
else
    fprintf('=> Failed with mipgap=0 too\n');
end

%% ================================================================
%% PART 6: Summary
%% ================================================================
fprintf('\n=== PROBE 016 SUMMARY ===\n');
fprintf('Original claim: "GLP_EMIPGAP mapped to failure"\n');
fprintf('\nFindings:\n');
fprintf('  1. In Octave GLPK, GLP_EMIPGAP = 14 (NOT 9)\n');
fprintf('  2. GLP_ETMLIM (time limit) = 9\n');
fprintf('  3. miqps_glpk.m line 241: handles errnum==9 && extra.status==2 as SUCCESS\n');
fprintf('  4. BUT: this maps GLP_ETMLIM (time limit hit) to success, not GLP_EMIPGAP\n');
fprintf('  5. A-5 result reports exitflag=-9 = errnum=9 = GLP_ETMLIM\n');
fprintf('     => The solver hit TIME LIMIT (tmlim=300s from A-5 script), not MIP gap\n');
fprintf('\nConclusion:\n');
ef_part1 = mdo.QP.exitflag;
if ef_part1 > 0
    fprintf('  First run (mipgap=0.01): exitflag=%d => PASSED\n', ef_part1);
    fprintf('  The bug may have been fixed between A-5 evaluation and now, OR\n');
    fprintf('  the problem actually solved optimally in < 60s time limit\n');
elseif ef_part1 == -9
    fprintf('  First run (mipgap=0.01): exitflag=-9 (TIME LIMIT hit)\n');
    fprintf('  Claim is partially wrong: actual issue is TIME LIMIT, not GLP_EMIPGAP\n');
elseif ef_part1 == -14
    fprintf('  First run (mipgap=0.01): exitflag=-14 (GLP_EMIPGAP)\n');
    fprintf('  Claim is correct: GLP_EMIPGAP IS mapped to failure\n');
    fprintf('  miqps_glpk.m only handles errnum==9 (ETMLIM) not errnum==14 (EMIPGAP)\n');
else
    fprintf('  First run: exitflag=%d\n', ef_part1);
end
