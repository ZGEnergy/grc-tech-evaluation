% Probe-028: Verify distributed slack DC OPF timing on ACTIVSg 10k
% Claim: 66 minutes total, ~65 min in MIPS solve (400x slower than single-slack)

mp_root = fullfile(pwd, 'matpower8.1');
addpath(fullfile(mp_root, 'lib'));
addpath(fullfile(mp_root, 'data'));
addpath(fullfile(mp_root, 'mips', 'lib'));
addpath(fullfile(mp_root, 'mp-opt-model', 'lib'));
addpath(fullfile(mp_root, 'mptest', 'lib'));

fprintf('=== Probe-028: Distributed Slack DC OPF Timing ===\n');
fprintf('MATPOWER version: %s\n', mpver());

% Load ACTIVSg 10k
fprintf('\nLoading ACTIVSg 10k...\n');
t0 = tic();
mpc = loadcase(fullfile('..', '..', 'data', 'networks', 'case_ACTIVSg10k.m'));
fprintf('Load time: %.2f s\n', toc(t0));
fprintf('Buses: %d, Branches: %d, Generators: %d\n', ...
        size(mpc.bus, 1), size(mpc.branch, 1), size(mpc.gen, 1));

% Step 1: Single-slack rundcopf
fprintf('\n--- Step 1: Single-slack rundcopf ---\n');
mpopt = mpoption('verbose', 0, 'out.all', 0);
t1 = tic();
result_ss = rundcopf(mpc, mpopt);
t_ss = toc(t1);
fprintf('Single-slack rundcopf time: %.2f s\n', t_ss);
fprintf('Success: %d, Objective: %.2f\n', result_ss.success, result_ss.f);

% Step 2: ext2int conversion
fprintf('\n--- Step 2: ext2int conversion ---\n');
t2 = tic();
mpc_int = ext2int(mpc);
t_ext2int = toc(t2);
fprintf('ext2int time: %.2f s\n', t_ext2int);

% Step 3: PTDF with distributed slack weights
fprintf('\n--- Step 3: Distributed-slack PTDF ---\n');
nb = size(mpc_int.bus, 1);
Pd = mpc_int.bus(:, 3);  % PD column
total_load = sum(Pd);
weights = Pd / total_load;
weights(weights < 0) = 0;
weights = weights / sum(weights);

t3 = tic();
H = makePTDF(mpc_int, weights);
t_ptdf = toc(t3);
fprintf('PTDF computation time: %.2f s\n', t_ptdf);
fprintf('PTDF size: %d x %d\n', size(H, 1), size(H, 2));

% Step 4: Build opt_model for distributed-slack DC OPF
fprintf('\n--- Step 4: Build opt_model ---\n');
t4 = tic();

% Constants
[PQ, PV, REF, NONE, BUS_I, BUS_TYPE, PD, QD, GS, BS, BUS_AREA, VM, ...
    VA, BASE_KV, ZONE, VMAX, VMIN, LAM_P, LAM_Q, MU_VMAX, MU_VMIN] = idx_bus;
[GEN_BUS, PG, QG, QMAX, QMIN, VG, MBASE, GEN_STATUS, PMAX, PMIN, ...
    MU_PMAX, MU_PMIN, MU_QMAX, MU_QMIN, PC1, PC2, QC1MIN, QC1MAX, ...
    QC2MIN, QC2MAX, RAMP_AGC, RAMP_10, RAMP_30, RAMP_Q, APF] = idx_gen;
[F_BUS, T_BUS, BR_R, BR_X, BR_B, RATE_A, RATE_B, RATE_C, ...
    TAP, SHIFT, BR_STATUS, PF, QF, PT, QT, MU_SF, MU_ST, ...
    ANGMIN, ANGMAX, MU_ANGMIN, MU_ANGMAX] = idx_brch;
[PW_LINEAR, POLYNOMIAL, MODEL, STARTUP, SHUTDOWN, NCOST, COST] = idx_cost;

% Only online generators
on = find(mpc_int.gen(:, GEN_STATUS) > 0);
ng = length(on);
nl = size(mpc_int.branch, 1);
fprintf('Online generators: %d\n', ng);

% Generator-bus incidence (only online gens)
Cg = sparse(mpc_int.gen(on, GEN_BUS), (1:ng)', 1, nb, ng);

% Build opt_model
om = opt_model();

% Variables: Pg (per-unit)
baseMVA = mpc_int.baseMVA;
om.add_var('Pg', ng, mpc_int.gen(on, PG) / baseMVA, ...
           mpc_int.gen(on, PMIN) / baseMVA, ...
           mpc_int.gen(on, PMAX) / baseMVA);

% Power balance: sum(Pg) = sum(Pd)  (scalar constraint via weights' * Cg * Pg = weights' * Pd)
Pd_pu = mpc_int.bus(:, PD) / baseMVA;
A_bal = weights' * Cg;  % 1 x ng
om.add_lin_constraint('Pbal', A_bal, sum(Pd_pu), sum(Pd_pu), {'Pg'});

% Branch flow limits using PTDF
rate_a = mpc_int.branch(:, RATE_A) / baseMVA;
active = rate_a > 0 & rate_a < (9999 / baseMVA);
na = sum(active);
fprintf('Active flow constraints: %d / %d\n', na, nl);

H_Cg = H(active, :) * Cg;
H_Pd = H(active, :) * Pd_pu;
A_flow = [H_Cg; -H_Cg];
u_flow = [rate_a(active) + H_Pd; rate_a(active) - H_Pd];
om.add_lin_constraint('flow', A_flow, [], u_flow, {'Pg'});

% Quadratic cost
gencost = mpc_int.gencost(on, :);
Q_diag = zeros(ng, 1);
c_vec = zeros(ng, 1);
for i = 1:ng
    if gencost(i, MODEL) == POLYNOMIAL
        nc = gencost(i, NCOST);
        if nc >= 3
            Q_diag(i) = 2 * gencost(i, COST) * baseMVA^2;
            c_vec(i) = gencost(i, COST + 1) * baseMVA;
        elseif nc == 2
            c_vec(i) = gencost(i, COST) * baseMVA;
        end
    end
end
om.add_quad_cost('gencost', sparse(1:ng, 1:ng, Q_diag, ng, ng), c_vec, 0, {'Pg'});

t_build = toc(t4);
fprintf('opt_model build time: %.2f s\n', t_build);
fprintf('Variables: %d, Constraints: %d\n', ng, 1 + 2 * na);

% Step 5: Solve with MIPS - limited iterations
fprintf('\n--- Step 5: MIPS solve (limited to 5 iterations) ---\n');

t5 = tic();
try
    mips_opt = struct('max_it', 5, 'verbose', 2);
    solve_opt = struct('alg', 'MIPS', ...
                       'mips_opt', mips_opt, ...
                       'verbose', 2);
    [x, f, eflag, output, lambda] = om.solve(solve_opt);
    t_solve = toc(t5);
    fprintf('MIPS solve (5 iters) time: %.2f s\n', t_solve);
    fprintf('Exit flag: %d\n', eflag);
    if isfield(output, 'iterations')
        fprintf('Iterations completed: %d\n', output.iterations);
        per_iter = t_solve / output.iterations;
    else
        per_iter = t_solve / 5;
    end
    fprintf('Per-iteration time: %.2f s\n', per_iter);
    fprintf('Estimated time for 50 iters:  %.1f s\n', per_iter * 50);
    fprintf('Estimated time for 100 iters: %.1f s\n', per_iter * 100);
    fprintf('Estimated time for 200 iters: %.1f s\n', per_iter * 200);
    fprintf('Estimated time for 500 iters: %.1f s\n', per_iter * 500);
catch e
    t_solve = toc(t5);
    fprintf('MIPS solve error after %.2f s: %s\n', t_solve, e.message);
end

% Summary
fprintf('\n=== TIMING SUMMARY ===\n');
fprintf('Single-slack rundcopf:   %.2f s\n', t_ss);
fprintf('ext2int:                 %.2f s\n', t_ext2int);
fprintf('Distributed-slack PTDF:  %.2f s\n', t_ptdf);
fprintf('opt_model build:         %.2f s\n', t_build);
fprintf('MIPS solve (5 iters):    %.2f s\n', t_solve);
fprintf('\nClaimed: MIPS solve ~3878s (~65 min), total ~3969s (~66 min)\n');
fprintf('Claimed: single-slack ~13s, distributed total ~66 min\n');
fprintf('Claimed slowdown: ~400x vs single-slack\n');
