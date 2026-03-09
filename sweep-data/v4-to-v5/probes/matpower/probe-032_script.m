% Probe-032: Verify MOST loadmd() failure on ACTIVSg 2000
% Claim: SCUC fails at loadmd() due to non-consecutive bus numbering

mp_root = fullfile(pwd, 'matpower8.1');
addpath(fullfile(mp_root, 'lib'));
addpath(fullfile(mp_root, 'data'));
addpath(fullfile(mp_root, 'mips', 'lib'));
addpath(fullfile(mp_root, 'mp-opt-model', 'lib'));
addpath(fullfile(mp_root, 'mptest', 'lib'));
addpath(fullfile(mp_root, 'most', 'lib'));

fprintf('=== Probe-032: MOST loadmd() on ACTIVSg 2000 ===\n');
fprintf('MATPOWER version: %s\n', mpver());

% Step 1: Load ACTIVSg 2000 and check bus numbering
fprintf('\n--- Step 1: Load ACTIVSg 2000 ---\n');
mpc = loadcase(fullfile('..', '..', 'data', 'networks', 'case_ACTIVSg2000.m'));
nb = size(mpc.bus, 1);
ng = size(mpc.gen, 1);
nl = size(mpc.branch, 1);
fprintf('Buses: %d, Generators: %d, Branches: %d\n', nb, ng, nl);

% Check consecutive bus numbering
bus_ids = mpc.bus(:, 1);
is_consecutive = isequal(bus_ids, (1:nb)');
fprintf('Bus IDs range: %d to %d\n', min(bus_ids), max(bus_ids));
fprintf('Consecutive numbering: %s\n', mat2str(is_consecutive));
if ~is_consecutive
    fprintf('Max bus ID: %d, Number of buses: %d (gap = %d)\n', ...
            max(bus_ids), nb, max(bus_ids) - nb);
    % Show first few non-consecutive IDs
    expected = (1:nb)';
    mismatches = find(bus_ids ~= expected, 5);
    if ~isempty(mismatches)
        fprintf('First mismatches at indices: ');
        fprintf('%d ', mismatches);
        fprintf('\n');
        for i = 1:min(3, length(mismatches))
            fprintf('  bus(%d) = %d, expected %d\n', ...
                    mismatches(i), bus_ids(mismatches(i)), ...
                    expected(mismatches(i)));
        end
    end
end

% Step 2: Verify that standard MATPOWER functions handle ext2int
fprintf('\n--- Step 2: Standard MATPOWER functions ---\n');
mpopt = mpoption('verbose', 0, 'out.all', 0);
try
    result = rundcpf(mpc, mpopt);
    fprintf('rundcpf: SUCCESS (handles ext2int transparently)\n');
catch e
    fprintf('rundcpf: FAILED - %s\n', e.message);
end

try
    result = rundcopf(mpc, mpopt);
    fprintf('rundcopf: SUCCESS (handles ext2int transparently)\n');
catch e
    fprintf('rundcopf: FAILED - %s\n', e.message);
end

% Step 3: Attempt MOST loadmd()
fprintf('\n--- Step 3: MOST loadmd() ---\n');

% Build a minimal MOST data structure (md)
% MOST requires: mpc, profiles for load/wind, and time horizon
nt = 24;  % 24 hours

% Create a minimal md struct
xgd_table = [];  % will try without extra gen data first

fprintf('Attempting loadmd with raw (non-consecutive) mpc...\n');
try
    % Build minimal xGenData
    xgd.CommitKey = ones(ng, 1);  % all committed
    % Try loadmd with the raw case
    md = loadmd(mpc, [], xgd, [], nt);
    fprintf('loadmd: SUCCESS (unexpected!)\n');
catch e
    fprintf('loadmd: FAILED\n');
    fprintf('Error message: %s\n', e.message);
    % Check if error mentions consecutive bus numbering
    if ~isempty(strfind(e.message, 'consecutive'))
        fprintf('>>> CONFIRMED: Error mentions consecutive bus numbering\n');
    elseif ~isempty(strfind(e.message, 'ext2int'))
        fprintf('>>> CONFIRMED: Error mentions ext2int\n');
    else
        fprintf('>>> Error does NOT mention consecutive/ext2int\n');
    end
end

% Step 4: Try with ext2int pre-converted case
fprintf('\n--- Step 4: loadmd() with ext2int pre-converted ---\n');
mpc_int = ext2int(mpc);
fprintf('ext2int conversion successful\n');
fprintf('Internal bus IDs: %d to %d (consecutive: %s)\n', ...
        min(mpc_int.bus(:, 1)), max(mpc_int.bus(:, 1)), ...
        mat2str(isequal(mpc_int.bus(:, 1), (1:size(mpc_int.bus, 1))')));

ng_int = size(mpc_int.gen, 1);
xgd_int.CommitKey = ones(ng_int, 1);

fprintf('Attempting loadmd with ext2int-converted mpc...\n');
try
    md = loadmd(mpc_int, [], xgd_int, [], nt);
    fprintf('loadmd: SUCCESS with ext2int-converted case\n');
catch e
    fprintf('loadmd: FAILED even with ext2int\n');
    fprintf('Error message: %s\n', e.message);
end

% Step 5: Check if loadmd calls ext2int internally
fprintf('\n--- Step 5: Inspect loadmd source ---\n');
which_loadmd = which('loadmd');
fprintf('loadmd location: %s\n', which_loadmd);

% Read first 50 lines of loadmd to check for ext2int handling
fid = fopen(which_loadmd, 'r');
if fid ~= -1
    found_ext2int = false;
    found_consecutive = false;
    for i = 1:100
        line = fgetl(fid);
        if ~ischar(line)
            break
        end
        if ~isempty(strfind(line, 'ext2int'))
            fprintf('Line %d: %s\n', i, strtrim(line));
            found_ext2int = true;
        end
        if ~isempty(strfind(line, 'consecutive'))
            fprintf('Line %d: %s\n', i, strtrim(line));
            found_consecutive = true;
        end
    end
    fclose(fid);
    if ~found_ext2int
        fprintf('No ext2int reference found in first 100 lines\n');
    end
    if ~found_consecutive
        fprintf('No "consecutive" reference found in first 100 lines\n');
    end
end

fprintf('\n=== SUMMARY ===\n');
fprintf('Claim: loadmd() fails with non-consecutive bus numbering\n');
fprintf('Claim: error message mentions consecutive bus numbering / ext2int\n');
fprintf('Claim: standard MATPOWER functions handle ext2int transparently\n');
