% Probe-029: Verify contingency sweep timing on ACTIVSg 10k
% Claim: 41 min total, 97% of time is Octave containers.Map overhead
% LODF screening itself only 50s for 28,035 cases

mp_root = fullfile(pwd, 'matpower8.1');
addpath(fullfile(mp_root, 'lib'));
addpath(fullfile(mp_root, 'data'));
addpath(fullfile(mp_root, 'mips', 'lib'));
addpath(fullfile(mp_root, 'mp-opt-model', 'lib'));
addpath(fullfile(mp_root, 'mptest', 'lib'));

fprintf('=== Probe-029: Contingency Sweep Timing ===\n');
fprintf('MATPOWER version: %s\n', mpver());

% Load ACTIVSg 10k
fprintf('\nLoading ACTIVSg 10k...\n');
t0 = tic();
mpc = loadcase(fullfile('..', '..', 'data', 'networks', 'case_ACTIVSg10k.m'));
fprintf('Load time: %.2f s\n', toc(t0));

nb = size(mpc.bus, 1);
nl = size(mpc.branch, 1);
ng = size(mpc.gen, 1);
fprintf('Buses: %d, Branches: %d, Generators: %d\n', nb, nl, ng);

% ext2int conversion
fprintf('\n--- ext2int conversion ---\n');
t_e = tic();
mpc_int = ext2int(mpc);
fprintf('ext2int time: %.2f s\n', toc(t_e));

nb_int = size(mpc_int.bus, 1);
nl_int = size(mpc_int.branch, 1);

% Step 1: PTDF computation
fprintf('\n--- Step 1: PTDF computation ---\n');
t1 = tic();
H = makePTDF(mpc_int);
t_ptdf = toc(t1);
fprintf('PTDF time: %.2f s (size: %d x %d)\n', t_ptdf, size(H, 1), size(H, 2));

% Step 2: LODF computation
fprintf('\n--- Step 2: LODF computation ---\n');
t2 = tic();
LODF = makeLODF(mpc_int.branch, H);
t_lodf = toc(t2);
fprintf('LODF time: %.2f s (size: %d x %d)\n', t_lodf, size(LODF, 1), size(LODF, 2));

fprintf('Total precompute: %.2f s\n', t_ptdf + t_lodf);

% Step 3: Run DC power flow for base case flows
fprintf('\n--- Step 3: Base case DC PF ---\n');
mpopt = mpoption('verbose', 0, 'out.all', 0);
t3 = tic();
result = rundcpf(mpc_int, mpopt);
t_pf = toc(t3);
fprintf('DC PF time: %.2f s\n', t_pf);

base_flow = result.branch(:, 14);  % PF column
rate_a = mpc_int.branch(:, 6);     % RATE_A column
fprintf('Base flows computed for %d branches\n', length(base_flow));

% Step 4: N-1 contingency screening using LODF (20 branches)
fprintf('\n--- Step 4: N-1 screening (first 20 branches) ---\n');
n_cont = min(20, nl_int);
violations = 0;

t4 = tic();
for k = 1:n_cont
    % Post-contingency flow for outage of branch k
    post_flow = base_flow + LODF(:, k) * base_flow(k);
    % Check violations (where rate > 0 and < 9999)
    valid = rate_a > 0 & rate_a < 9999;
    viol = abs(post_flow) > rate_a & valid;
    violations = violations + sum(viol);
end
t_n1_20 = toc(t4);
fprintf('N-1 screening (20 branches): %.4f s, violations: %d\n', t_n1_20, violations);
fprintf('Per-contingency: %.6f s\n', t_n1_20 / n_cont);

% Step 5: N-1 screening on ALL branches
fprintf('\n--- Step 5: N-1 screening (ALL %d branches) ---\n', nl_int);
violations_all = 0;
t5 = tic();
for k = 1:nl_int
    post_flow = base_flow + LODF(:, k) * base_flow(k);
    valid = rate_a > 0 & rate_a < 9999;
    viol = abs(post_flow) > rate_a & valid;
    violations_all = violations_all + sum(viol);
end
t_n1_all = toc(t5);
fprintf('N-1 screening (all branches): %.2f s, violations: %d\n', t_n1_all, violations_all);
fprintf('Per-contingency: %.6f s\n', t_n1_all / nl_int);

% Step 6: BFS adjacency construction using containers.Map (the claimed bottleneck)
fprintf('\n--- Step 6: BFS adjacency via containers.Map ---\n');
fprintf('Building adjacency map for %d buses...\n', nb_int);

t6 = tic();
adj = containers.Map('KeyType', 'int32', 'ValueType', 'any');
for i = 1:nb_int
    adj(i) = [];
end
% Add edges from branch data
for k = 1:nl_int
    fb = mpc_int.branch(k, 1);  % F_BUS
    tb = mpc_int.branch(k, 2);  % T_BUS
    adj(fb) = [adj(fb), tb];
    adj(tb) = [adj(tb), fb];
end
t_adj = toc(t6);
fprintf('Adjacency map construction: %.2f s\n', t_adj);

% Step 7: BFS from a bus (bus 6072 equivalent in internal ordering)
fprintf('\n--- Step 7: BFS traversal (depth 5) ---\n');
% Find bus closest to 6072 in internal numbering
start_bus = 1;  % Use bus 1 for simplicity
visited = containers.Map('KeyType', 'int32', 'ValueType', 'logical');
visited(start_bus) = true;
current_level = [start_bus];

t7 = tic();
for depth = 1:5
    next_level = [];
    for i = 1:length(current_level)
        bus = current_level(i);
        neighbors = adj(bus);
        for j = 1:length(neighbors)
            nb_j = neighbors(j);
            if ~visited.isKey(nb_j)
                visited(nb_j) = true;
                next_level = [next_level, nb_j];
            end
        end
    end
    current_level = next_level;
    fprintf('  Depth %d: %d new buses found\n', depth, length(next_level));
end
t_bfs = toc(t7);
fprintf('BFS time: %.2f s, total buses reached: %d\n', t_bfs, visited.Count);

% Step 8: Estimate containers.Map overhead with a scaling test
fprintf('\n--- Step 8: containers.Map scaling test ---\n');
% Time inserting/reading N elements
for N = [1000, 5000, 10000]
    t_test = tic();
    m = containers.Map('KeyType', 'int32', 'ValueType', 'any');
    for i = 1:N
        m(i) = i;
    end
    for i = 1:N
        x = m(i);
    end
    t_map = toc(t_test);
    fprintf('  Map ops (N=%d): %.3f s (%.1f us/op)\n', N, t_map, t_map / (2 * N) * 1e6);
end

% Summary
fprintf('\n=== TIMING SUMMARY ===\n');
fprintf('PTDF computation:          %.2f s\n', t_ptdf);
fprintf('LODF computation:          %.2f s\n', t_lodf);
fprintf('DC PF (base case):         %.2f s\n', t_pf);
fprintf('N-1 screening (20):        %.4f s\n', t_n1_20);
fprintf('N-1 screening (all %d):  %.2f s\n', nl_int, t_n1_all);
fprintf('Adjacency map build:       %.2f s\n', t_adj);
fprintf('BFS traversal (depth 5):   %.2f s\n', t_bfs);
fprintf('\nClaimed: 41 min total, of which:\n');
fprintf('  - PTDF+LODF precompute: 29s\n');
fprintf('  - BFS + adjacency build: ~2400s (containers.Map bottleneck)\n');
fprintf('  - N-1 through N-4 screening: 50.4s\n');
fprintf('\nProbe adjacency build: %.2f s\n', t_adj);
fprintf('Extrapolated N-2/N-3/N-4 adjacency cost would be higher due to combo enumeration\n');
