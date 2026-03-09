% Probe-032c: Verify MOST loadmd() bus numbering failure on ACTIVSg 2000
% With all required xGenData fields

mp_root = fullfile(pwd, 'matpower8.1');
addpath(fullfile(mp_root, 'lib'));
addpath(fullfile(mp_root, 'data'));
addpath(fullfile(mp_root, 'mips', 'lib'));
addpath(fullfile(mp_root, 'mp-opt-model', 'lib'));
addpath(fullfile(mp_root, 'mptest', 'lib'));
addpath(fullfile(mp_root, 'most', 'lib'));

fprintf('=== Probe-032c: MOST loadmd() Bus Numbering ===\n');

% Load ACTIVSg 2000
mpc = loadcase(fullfile('..', '..', 'data', 'networks', 'case_ACTIVSg2000.m'));
ng = size(mpc.gen, 1);
fprintf('ACTIVSg 2000: %d buses, %d gens, bus IDs %d-%d\n', ...
        size(mpc.bus, 1), ng, min(mpc.bus(:, 1)), max(mpc.bus(:, 1)));

% Build complete xGenData with ALL required fields
xgd = struct();
xgd.CommitSched = ones(ng, 1);
xgd.InitialPg = mpc.gen(:, 2);  % PG column = current dispatch
xgd.RampWearCostCoeff = zeros(ng, 1);
xgd.PositiveActiveReservePrice = zeros(ng, 1);
xgd.PositiveActiveReserveQuantity = zeros(ng, 1);
xgd.NegativeActiveReservePrice = zeros(ng, 1);
xgd.NegativeActiveReserveQuantity = zeros(ng, 1);
xgd.PositiveActiveDeltaPrice = zeros(ng, 1);
xgd.NegativeActiveDeltaPrice = zeros(ng, 1);
xgd.PositiveLoadFollowReservePrice = zeros(ng, 1);
xgd.PositiveLoadFollowReserveQuantity = zeros(ng, 1);
xgd.NegativeLoadFollowReservePrice = zeros(ng, 1);
xgd.NegativeLoadFollowReserveQuantity = zeros(ng, 1);

nt = 24;

% Test 1: loadmd with non-consecutive bus numbering
fprintf('\n--- Test 1: loadmd on raw ACTIVSg 2000 (non-consecutive) ---\n');
try
    md = loadmd(mpc, [], xgd, [], nt);
    fprintf('loadmd: SUCCESS (unexpected)\n');
catch e
    fprintf('loadmd: FAILED\n');
    fprintf('Error: %s\n', e.message);
    if ~isempty(strfind(e.message, 'consecutively'))
        fprintf('>>> CONFIRMED: fails with consecutive bus numbering error\n');
    elseif ~isempty(strfind(e.message, 'consecutive'))
        fprintf('>>> CONFIRMED: fails with consecutive bus numbering error\n');
    else
        fprintf('>>> Different error than expected\n');
    end
end

% Test 2: loadmd with ext2int-converted case
fprintf('\n--- Test 2: loadmd on ext2int-converted ACTIVSg 2000 ---\n');
mpc_int = ext2int(mpc);
ng_int = size(mpc_int.gen, 1);
fprintf('Internal: %d buses, %d gens (ext2int removed %d offline gens)\n', ...
        size(mpc_int.bus, 1), ng_int, ng - ng_int);

xgd_int = struct();
xgd_int.CommitSched = ones(ng_int, 1);
xgd_int.InitialPg = mpc_int.gen(:, 2);
xgd_int.RampWearCostCoeff = zeros(ng_int, 1);
xgd_int.PositiveActiveReservePrice = zeros(ng_int, 1);
xgd_int.PositiveActiveReserveQuantity = zeros(ng_int, 1);
xgd_int.NegativeActiveReservePrice = zeros(ng_int, 1);
xgd_int.NegativeActiveReserveQuantity = zeros(ng_int, 1);
xgd_int.PositiveActiveDeltaPrice = zeros(ng_int, 1);
xgd_int.NegativeActiveDeltaPrice = zeros(ng_int, 1);
xgd_int.PositiveLoadFollowReservePrice = zeros(ng_int, 1);
xgd_int.PositiveLoadFollowReserveQuantity = zeros(ng_int, 1);
xgd_int.NegativeLoadFollowReservePrice = zeros(ng_int, 1);
xgd_int.NegativeLoadFollowReserveQuantity = zeros(ng_int, 1);

try
    md = loadmd(mpc_int, [], xgd_int, [], nt);
    fprintf('loadmd: SUCCESS with ext2int\n');
    fprintf('>>> Confirms failure is bus-numbering, not data format\n');
catch e
    fprintf('loadmd: FAILED even with ext2int\n');
    fprintf('Error: %s\n', e.message);
end

% Test 3: Control with case39 (consecutive buses)
fprintf('\n--- Test 3: loadmd on case39 (consecutive, control) ---\n');
mpc39 = loadcase(fullfile('..', '..', 'data', 'networks', 'case39.m'));
ng39 = size(mpc39.gen, 1);

xgd39 = struct();
xgd39.CommitSched = ones(ng39, 1);
xgd39.InitialPg = mpc39.gen(:, 2);
xgd39.RampWearCostCoeff = zeros(ng39, 1);
xgd39.PositiveActiveReservePrice = zeros(ng39, 1);
xgd39.PositiveActiveReserveQuantity = zeros(ng39, 1);
xgd39.NegativeActiveReservePrice = zeros(ng39, 1);
xgd39.NegativeActiveReserveQuantity = zeros(ng39, 1);
xgd39.PositiveActiveDeltaPrice = zeros(ng39, 1);
xgd39.NegativeActiveDeltaPrice = zeros(ng39, 1);
xgd39.PositiveLoadFollowReservePrice = zeros(ng39, 1);
xgd39.PositiveLoadFollowReserveQuantity = zeros(ng39, 1);
xgd39.NegativeLoadFollowReservePrice = zeros(ng39, 1);
xgd39.NegativeLoadFollowReserveQuantity = zeros(ng39, 1);

try
    md = loadmd(mpc39, [], xgd39, [], nt);
    fprintf('loadmd: SUCCESS on case39\n');
catch e
    fprintf('loadmd: FAILED on case39\n');
    fprintf('Error: %s\n', e.message);
end

fprintf('\n=== SUMMARY ===\n');
