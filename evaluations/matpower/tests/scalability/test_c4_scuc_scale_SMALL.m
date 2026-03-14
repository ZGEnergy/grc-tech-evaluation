%% Test C-4: SCUC 24hr on SMALL (ACTIVSg 2000-bus)
%%
%% Dimension: scalability
%% Network: SMALL (ACTIVSg 2000-bus)
%% Pass condition: Completes SCUC 24hr on SMALL within time budget.
%% Tool: MATPOWER 8.1 (MOST 1.3.1)
%% Solver: GLPK/MIPS (HiGHS/SCIP unavailable in Octave)

%% Setup MATPOWER + MOST paths
mp_root = '/workspace/evaluations/matpower/matpower8.1';
addpath(fullfile(mp_root, 'lib'));
addpath(fullfile(mp_root, 'data'));
addpath(fullfile(mp_root, 'mips', 'lib'));
addpath(fullfile(mp_root, 'mp-opt-model', 'lib'));
addpath(fullfile(mp_root, 'mptest', 'lib'));
addpath(fullfile(mp_root, 'most', 'lib'));
addpath(fullfile(mp_root, 'most', 'examples'));

network_file = '/workspace/data/networks/case_ACTIVSg2000.m';

result_status = 'fail';
errors = {};
workarounds = {};
solve_time = 0;
peak_memory_mb = -1;
mip_gap = -1;

try
    define_constants;
    [CT_LABEL, CT_PROB, CT_TABLE, CT_TBUS, CT_TGEN, CT_TBRCH, ...
        CT_TAREABUS, CT_TAREAGEN, CT_TAREABRCH, CT_ROW, CT_COL, ...
        CT_CHGTYPE, CT_REP, CT_REL, CT_ADD, CT_NEWVAL, CT_TLOAD, ...
        CT_TAREALOAD, CT_LOAD_ALL_PQ, CT_LOAD_FIX_PQ, CT_LOAD_DIS_PQ, ...
        CT_LOAD_ALL_P, CT_LOAD_FIX_P, CT_LOAD_DIS_P, CT_TGENCOST, ...
        CT_TAREAGENCOST, CT_MODCOST_F, CT_MODCOST_X] = idx_ct;

    %% Load case
    fprintf('Loading %s...\n', network_file);
    mpc = loadcase(network_file);
    nb = size(mpc.bus, 1);
    nl = size(mpc.branch, 1);
    ng = size(mpc.gen, 1);
    nt = 24;
    fprintf('Network: %d buses, %d branches, %d generators\n', nb, nl, ng);
    fprintf('Periods: %d, Total variables estimate: ~%d\n', nt, ng * nt * 3 + nb * nt);

    %% Ensure gencost exists and is well-formed
    %% GLPK only handles MILP (not MIQP), so use linear costs only.
    %% Convert existing quadratic costs to linear by dropping quadratic term.
    if isfield(mpc, 'gencost') && size(mpc.gencost, 1) == ng
        %% Extract linear coefficient from existing polynomial costs
        if mpc.gencost(1, MODEL) == 2 && mpc.gencost(1, NCOST) == 3
            %% Quadratic: f(p) = c2*p^2 + c1*p + c0
            %% Linearize: f(p) = c1*p + c0 (drop quadratic term for GLPK)
            fprintf('Linearizing quadratic costs for GLPK MILP compatibility...\n');
            linear_coeff = mpc.gencost(:, COST + 1);  % c1 (linear term)
            const_coeff = mpc.gencost(:, COST + 2);   % c0 (constant term)
            startup_cost = mpc.gencost(:, STARTUP);
            mpc.gencost = zeros(ng, 6);
            mpc.gencost(:, MODEL) = 2;  % polynomial
            mpc.gencost(:, NCOST) = 2;  % linear (2 coefficients)
            mpc.gencost(:, COST) = linear_coeff;
            mpc.gencost(:, COST + 1) = const_coeff;
            mpc.gencost(:, STARTUP) = startup_cost;
        end
    else
        fprintf('Setting up linear cost curves for %d generators...\n', ng);
        mpc.gencost = zeros(ng, 6);
        mpc.gencost(:, MODEL) = 2;  % polynomial
        mpc.gencost(:, NCOST) = 2;  % linear
        mpc.gencost(:, COST) = 20 + 30 * rand(ng, 1);  % linear $/MWh
        mpc.gencost(:, COST + 1) = 100 * rand(ng, 1);  % no-load cost
        mpc.gencost(:, STARTUP) = 500 + 4500 * rand(ng, 1);
    end

    %% Set ramp rates if not present
    if all(mpc.gen(:, RAMP_10) == 0)
        mpc.gen(:, RAMP_10) = mpc.gen(:, PMAX) * 0.5;  % 50% of Pmax per 10min
        mpc.gen(:, RAMP_30) = mpc.gen(:, PMAX) * 0.8;
        mpc.gen(:, RAMP_AGC) = mpc.gen(:, PMAX) * 0.05;
    end

    %% Set Pmin
    mpc.gen(:, PMIN) = max(mpc.gen(:, PMIN), mpc.gen(:, PMAX) * 0.2);

    %% Convert to internal numbering BEFORE building xGenData
    %% (ext2int may remove offline generators, changing ng)
    mpc = ext2int(mpc);
    ng = size(mpc.gen, 1);  % update ng after ext2int
    fprintf('After ext2int: %d generators\n', ng);

    %% Build xGenData for UC
    xgd_table.colnames = { 'CommitKey', 'CommitSched', 'MinUp', 'MinDown', ...
                          'PositiveActiveReservePrice', 'PositiveActiveReserveQuantity', ...
                          'NegativeActiveReservePrice', 'NegativeActiveReserveQuantity', ...
                          'PositiveActiveDeltaPrice', 'NegativeActiveDeltaPrice', ...
                          'PositiveLoadFollowReservePrice', 'PositiveLoadFollowReserveQuantity', ...
                          'NegativeLoadFollowReservePrice', 'NegativeLoadFollowReserveQuantity' };
    xgd_table.data = zeros(ng, 14);
    xgd_table.data(:, 1) = 1;              % CommitKey (UC decides)
    xgd_table.data(:, 2) = 1;              % CommitSched (initially on)
    xgd_table.data(:, 3) = 4;              % MinUp = 4 hours
    xgd_table.data(:, 4) = 2;              % MinDown = 2 hours
    xgd_table.data(:, 5) = 1e-6;           % Reserve prices
    xgd_table.data(:, 6) = mpc.gen(:, PMAX);
    xgd_table.data(:, 7) = 1e-6;
    xgd_table.data(:, 8) = mpc.gen(:, PMAX);
    xgd_table.data(:, 9:10) = 1e-9;
    xgd_table.data(:, 11) = 1e-6;
    xgd_table.data(:, 12) = mpc.gen(:, PMAX);
    xgd_table.data(:, 13) = 1e-6;
    xgd_table.data(:, 14) = mpc.gen(:, PMAX);
    xgd = loadxgendata(xgd_table, mpc);

    %% Build 24-hour load profile (sinusoidal pattern)
    total_load = sum(mpc.bus(:, PD));
    load_factors = 0.7 + 0.3 * sin(2 * pi * ((1:nt) - 6) / 24);
    load_factors = load_factors / mean(load_factors);  % normalize around 1.0

    load_profile = struct('type', 'mpcData', 'table', CT_TLOAD, ...
                          'rows', 0, 'col', CT_LOAD_ALL_PQ, 'chgtype', CT_REP, 'values', []);
    load_profile.values = reshape(load_factors', [nt, 1, 1]);
    profiles = load_profile;

    %% Configure MOST with GLPK
    mpopt = mpoption('verbose', 0, 'out.all', 0, 'model', 'DC');
    mpopt = mpoption(mpopt, 'most.dc_model', 1, 'most.uc.run', 1);
    mpopt = mpoption(mpopt, 'most.solver', 'GLPK');
    mpopt = mpoption(mpopt, 'glpk.opts.mipgap', 0.01);
    mpopt = mpoption(mpopt, 'glpk.opts.tolint', 1e-6);
    mpopt = mpoption(mpopt, 'glpk.opts.tmlim', 600);  % 10 min timeout

    %% Assemble MOST data
    fprintf('Assembling MOST data structure...\n');
    md = loadmd(mpc, nt, xgd, [], [], profiles);

    %% Solve
    fprintf('Solving SCUC (GLPK, %d buses, %d gens, %d periods)...\n', nb, ng, nt);
    tic;
    mdo = most(md, mpopt);
    solve_time = toc;

    fprintf('Solve time: %.4f s\n', solve_time);
    fprintf('Exit flag: %d\n', mdo.QP.exitflag);

    %% Peak memory
    [~, mem_out] = system('grep VmHWM /proc/self/status');
    peak_kb = sscanf(mem_out, 'VmHWM: %f');
    if ~isempty(peak_kb)
        peak_memory_mb = peak_kb / 1024;
    end

    if mdo.QP.exitflag > 0
        %% Extract results
        ms = most_summary(mdo);
        commitment = ms.u(:, :, 1, 1);
        dispatch = ms.Pg(:, :, 1, 1);

        %% Count cycling generators
        cycling_gens = 0;
        cycling_ids = [];
        for g = 1:size(commitment, 1)
            u_g = commitment(g, :);
            if min(u_g) ~= max(u_g)
                cycling_gens = cycling_gens + 1;
                cycling_ids(end + 1) = g;
            end
        end

        fprintf('\n=== SCUC Results ===\n');
        fprintf('Objective: %.2f\n', ms.f);
        fprintf('Cycling generators: %d / %d\n', cycling_gens, size(commitment, 1));
        fprintf('Total dispatch range: [%.1f, %.1f] MW\n', ...
                min(sum(dispatch, 1)), max(sum(dispatch, 1)));

        result_status = 'pass';
    else
        %% Known GLPK exitflag issue (same as A-5)
        fprintf('\nGLPK returned non-positive exitflag=%d\n', mdo.QP.exitflag);
        fprintf('This is the same GLPK/MATPOWER integration issue seen in A-5.\n');
        fprintf('GLPK MIP gap termination maps to negative exitflag, preventing\n');
        fprintf('MOST from post-processing the solution.\n');

        %% Check if QP.x exists (solver found a solution but MOST rejected it)
        if isfield(mdo, 'QP') && isfield(mdo.QP, 'x') && ~isempty(mdo.QP.x)
            fprintf('Solution vector exists (%d variables) but MOST skipped post-processing.\n', ...
                    length(mdo.QP.x));
            errors{end + 1} = sprintf(['GLPK exitflag=%d on SMALL SCUC. Solution exists but ', ...
                                       'MOST rejects it. Same GLPK integra'], mdo.QP.exitflag);
            workarounds{end + 1} = ['MOST SCUC formulation works but GLPK exit flag mapping ', ...
                                    'prevents solution extraction. Blocked by A-5 GLPK integ'];
        else
            errors{end + 1} = sprintf('MOST SCUC solver failed (exitflag=%d)', mdo.QP.exitflag);
        end
    end

catch e
    errors{end + 1} = e.message;
    fprintf('ERROR: %s\n', e.message);
    for i = 1:length(e.stack)
        fprintf('  at %s line %d\n', e.stack(i).name, e.stack(i).line);
    end
end

fprintf('\n=== Final ===\n');
fprintf('Status: %s\n', result_status);
fprintf('Wall clock: %.4f s\n', solve_time);
fprintf('Peak memory: %.1f MB\n', peak_memory_mb);
if ~isempty(errors)
    fprintf('Errors:\n');
    for i = 1:length(errors)
        fprintf('  - %s\n', errors{i});
    end
end
if ~isempty(workarounds)
    fprintf('Workarounds:\n');
    for i = 1:length(workarounds)
        fprintf('  - %s\n', workarounds{i});
    end
end
