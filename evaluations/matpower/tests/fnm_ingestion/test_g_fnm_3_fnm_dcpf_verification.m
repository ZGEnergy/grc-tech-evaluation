%% Test G-FNM-3: DCPF verification against reference solution on cleaned FNM
%%
%% Dimension: fnm_ingestion
%% Network: LARGE (FNM Annual S01 -- main island, pre-cleaned .mat)
%% Pass condition: Pass if all aggregate thresholds are met and no hard-fail
%%   condition is triggered, per the dcpf section of pass_conditions.json.
%%   Bus angle: >=95% within 1.0 deg. Branch flow: >=90% within 10% relative.
%%   Hard-fail: >20% bus or branch failures, or any branch >50% deviation.
%% Tool: MATPOWER 8.1
%% Input path: matpower (fallback .mat file)

fprintf('\n=== G-FNM-3: DCPF Verification on Cleaned FNM ===\n\n');

%% Setup MATPOWER
mp_root = '/workspace/evaluations/matpower/matpower8.1';
addpath(fullfile(mp_root, 'lib'));
addpath(fullfile(mp_root, 'data'));
addpath(fullfile(mp_root, 'mips', 'lib'));
addpath(fullfile(mp_root, 'mp-opt-model', 'lib'));
addpath(fullfile(mp_root, 'mptest', 'lib'));
addpath('/workspace/evaluations/matpower/tests/fnm_ingestion');

define_constants;

%% Load cleaned FNM case
fprintf('Loading cleaned FNM case...\n');
mat_path = '/workspace/data/fnm/reference/cleaned/fnm_main_island.mat';
mpc = loadcase(mat_path);
fprintf('  Buses: %d\n', size(mpc.bus, 1));
fprintf('  Branches: %d\n', size(mpc.branch, 1));
fprintf('  Generators: %d\n', size(mpc.gen, 1));
fprintf('  baseMVA: %.1f\n', mpc.baseMVA);

%% Load excluded buses
fprintf('\nLoading excluded buses...\n');
excluded_json = fileread('/workspace/data/fnm/reference/excluded_buses.json');
excluded_buses = [];
[tok] = regexp(excluded_json, '"bus_number":\s*(\d+)', 'tokens');
for i = 1:length(tok)
    excluded_buses(end + 1) = str2double(tok{i}{1});
end
fprintf('  Excluded buses: %d\n', length(excluded_buses));

%% Solve DCPF
fprintf('\nSolving DCPF...\n');
mpopt = mpoption('verbose', 0, 'out.all', 0);

[~, rss_txt] = system('grep VmHWM /proc/self/status');
rss_before = sscanf(rss_txt, 'VmHWM: %f') / 1024;

tic_solve = tic;
results = rundcpf(mpc, mpopt);
solve_time = toc(tic_solve);

[~, rss_txt] = system('grep VmHWM /proc/self/status');
rss_after = sscanf(rss_txt, 'VmHWM: %f') / 1024;

fprintf('  DCPF success: %d\n', results.success);
fprintf('  Wall clock: %.3f seconds\n', solve_time);
fprintf('  Peak RSS: %.1f MB\n', rss_after);

if ~results.success
    fprintf('\nRESULT: FAIL -- DCPF did not converge\n');
    return
end

%% Load reference DCPF solution
fprintf('\nLoading reference DCPF solution...\n');
ref_buses_file = '/workspace/data/fnm/reference/dcpf/buses_dcpf.csv';
ref_branches_file = '/workspace/data/fnm/reference/dcpf/branches_dcpf.csv';

ref_bus_data = dlmread(ref_buses_file, ',', 1, 0);
ref_bus_numbers = ref_bus_data(:, 1);
ref_va_deg = ref_bus_data(:, 2);
ref_base_kv = ref_bus_data(:, 4);
fprintf('  Reference buses: %d\n', length(ref_bus_numbers));

ref_branch_data = dlmread(ref_branches_file, ',', 1, 0);
ref_from_bus = ref_branch_data(:, 1);
ref_to_bus = ref_branch_data(:, 2);
ref_pf_mw = ref_branch_data(:, 3);
ref_br_status = ref_branch_data(:, 4);
fprintf('  Reference branches: %d\n', length(ref_from_bus));

%% Compare bus voltage angles (vectorized)
fprintf('\n--- Bus Angle Comparison ---\n');

tool_bus_numbers = results.bus(:, BUS_I);
tool_va_deg = results.bus(:, VA);

% Build exclusion mask using ismember (vectorized, fast)
ref_excluded_mask = ismember(ref_bus_numbers, excluded_buses);
ref_non_excluded = ~ref_excluded_mask;
non_excluded_count = sum(ref_non_excluded);
fprintf('  Non-excluded reference buses: %d\n', non_excluded_count);

% Match reference buses to tool buses (vectorized)
[found_in_tool, tool_idx] = ismember(ref_bus_numbers, tool_bus_numbers);

% Valid = non-excluded AND found in tool
valid_mask = ref_non_excluded & found_in_tool;
valid_ref_va = ref_va_deg(valid_mask);
valid_tool_va = tool_va_deg(tool_idx(valid_mask));
valid_base_kv = ref_base_kv(valid_mask);
valid_bus_nums = ref_bus_numbers(valid_mask);

va_deviations = abs(valid_tool_va - valid_ref_va);

% Buses not found in tool count as failing
not_found_count = sum(ref_non_excluded & ~found_in_tool);

% Pass/fail counts
passing_mask = va_deviations < 1.0;
passing_bus_count = sum(passing_mask);
failing_bus_count = sum(~passing_mask) + not_found_count;

max_va_dev = max(va_deviations);
bus_passing_frac = passing_bus_count / non_excluded_count;
bus_failing_frac = failing_bus_count / non_excluded_count;

fprintf('  Passing (|VA_dev| < 1.0 deg): %d (%.2f%%)\n', passing_bus_count, bus_passing_frac * 100);
fprintf('  Failing: %d (%.2f%%)\n', failing_bus_count, bus_failing_frac * 100);
fprintf('  Not found in tool: %d\n', not_found_count);
fprintf('  Max VA deviation: %.4f deg\n', max_va_dev);
fprintf('  Mean VA deviation: %.6f deg\n', mean(va_deviations));
fprintf('  Median VA deviation: %.6f deg\n', median(va_deviations));

% Percentiles
sorted_dev = sort(va_deviations);
n_dev = length(sorted_dev);
fprintf('  P95 VA deviation: %.6f deg\n', sorted_dev(ceil(0.95 * n_dev)));
fprintf('  P99 VA deviation: %.6f deg\n', sorted_dev(ceil(0.99 * n_dev)));

% Voltage level breakdown
fprintf('\n  Voltage level breakdown (VA deviations):\n');
mask_230 = valid_base_kv >= 230;
mask_69 = (valid_base_kv >= 69) & (valid_base_kv < 230);
mask_low = valid_base_kv < 69;
if any(mask_230)
    fprintf('    >= 230 kV: n=%d, mean=%.6f, median=%.6f, max=%.4f\n', ...
            sum(mask_230), mean(va_deviations(mask_230)), median(va_deviations(mask_230)), ...
            max(va_deviations(mask_230)));
end
if any(mask_69)
    fprintf('    69-229 kV: n=%d, mean=%.6f, median=%.6f, max=%.4f\n', ...
            sum(mask_69), mean(va_deviations(mask_69)), median(va_deviations(mask_69)), ...
            max(va_deviations(mask_69)));
end
if any(mask_low)
    fprintf('    < 69 kV: n=%d, mean=%.6f, median=%.6f, max=%.4f\n', ...
            sum(mask_low), mean(va_deviations(mask_low)), median(va_deviations(mask_low)), ...
            max(va_deviations(mask_low)));
end

% Show top failing buses
failing_idx = find(~passing_mask);
if ~isempty(failing_idx)
    n_show = min(20, length(failing_idx));
    fprintf('\n  Sample failing buses (top %d by deviation):\n', n_show);
    [~, sorted_fail_idx] = sort(va_deviations(failing_idx), 'descend');
    for j = 1:n_show
        fi = failing_idx(sorted_fail_idx(j));
        fprintf('    Bus %d: VA_tool=%.4f VA_ref=%.4f dev=%.4f deg (%.1f kV)\n', ...
                valid_bus_nums(fi), valid_tool_va(fi), valid_ref_va(fi), va_deviations(fi), ...
                valid_base_kv(fi));
    end
end

%% Compare branch flows (vectorized)
fprintf('\n--- Branch Flow Comparison ---\n');

% Reference CSV contains only in-service branches.
% Tool results include all branches (in-service + out-of-service).
% Filter tool branches to in-service only, then compare positionally.
tool_br_status_col = results.branch(:, BR_STATUS);
tool_in_service_mask = tool_br_status_col == 1;
tool_pf_is = results.branch(tool_in_service_mask, PF);
tool_from_is = results.branch(tool_in_service_mask, F_BUS);
tool_to_is = results.branch(tool_in_service_mask, T_BUS);

n_ref_branches = length(ref_from_bus);
n_tool_is_branches = length(tool_pf_is);
fprintf('  Reference branches (in-service): %d\n', n_ref_branches);
fprintf('  Tool in-service branches: %d\n', n_tool_is_branches);

% All ref branches are in-service (ref_br_status all == 1)
in_service_count = min(n_ref_branches, n_tool_is_branches);

tool_p_is = tool_pf_is(1:in_service_count);
ref_p_is = ref_pf_mw(1:in_service_count);
from_is = ref_from_bus(1:in_service_count);
to_is = ref_to_bus(1:in_service_count);

denom = max(abs(ref_p_is), 1.0);
branch_dev_pct = abs(tool_p_is - ref_p_is) ./ denom * 100;

branch_passing_mask = branch_dev_pct < 10.0;
branch_passing = sum(branch_passing_mask);
branch_failing = sum(~branch_passing_mask);
max_branch_dev_pct = max(branch_dev_pct);

branch_passing_frac = branch_passing / in_service_count;
branch_failing_frac = branch_failing / in_service_count;

fprintf('  In-service branches: %d\n', in_service_count);
fprintf('  Passing (dev < 10%%): %d (%.2f%%)\n', branch_passing, branch_passing_frac * 100);
fprintf('  Failing: %d (%.2f%%)\n', branch_failing, branch_failing_frac * 100);
fprintf('  Max branch deviation: %.2f%%\n', max_branch_dev_pct);
fprintf('  Mean branch deviation: %.4f%%\n', mean(branch_dev_pct));
fprintf('  Median branch deviation: %.6f%%\n', median(branch_dev_pct));

% Show top failing branches
br_failing_idx = find(~branch_passing_mask);
if ~isempty(br_failing_idx)
    n_show = min(20, length(br_failing_idx));
    fprintf('\n  Sample failing branches (top %d by deviation):\n', n_show);
    [~, sorted_br_idx] = sort(branch_dev_pct(br_failing_idx), 'descend');
    for j = 1:n_show
        bi = br_failing_idx(sorted_br_idx(j));
        fprintf('    Branch %d->%d: P_tool=%.2f P_ref=%.2f dev=%.2f%%\n', ...
                from_is(bi), to_is(bi), tool_p_is(bi), ref_p_is(bi), branch_dev_pct(bi));
    end
end

%% Pass/Fail Assessment
fprintf('\n--- Pass/Fail Assessment ---\n');

hard_fail = false;
hard_fail_reasons = {};

if bus_failing_frac > 0.2
    hard_fail = true;
    hard_fail_reasons{end + 1} = sprintf('excessive_bus_failing_fraction: %.2f%% > 20%%', ...
                                         bus_failing_frac * 100);
end
if branch_failing_frac > 0.2
    hard_fail = true;
    hard_fail_reasons{end + 1} = sprintf('excessive_branch_failing_fraction: %.2f%% > 20%%', ...
                                         branch_failing_frac * 100);
end
if max_branch_dev_pct > 50.0
    hard_fail = true;
    hard_fail_reasons{end + 1} = sprintf('extreme_branch_flow_deviation: %.2f%% > 50%%', ...
                                         max_branch_dev_pct);
end

bus_passes = bus_passing_frac >= 0.95;
branch_passes = branch_passing_frac >= 0.90;

if hard_fail
    overall_status = 'FAIL';
    fprintf('  HARD FAIL triggered:\n');
    for i = 1:length(hard_fail_reasons)
        fprintf('    - %s\n', hard_fail_reasons{i});
    end
elseif bus_passes && branch_passes
    overall_status = 'PASS';
else
    overall_status = 'FAIL';
end

if bus_passes
    bus_label = 'PASS';
else
    bus_label = 'FAIL';
end
if branch_passes
    branch_label = 'PASS';
else
    branch_label = 'FAIL';
end

fprintf('\n  Bus angle gate (>= 95%%): %.2f%% -- %s\n', bus_passing_frac * 100, bus_label);
fprintf('  Branch flow gate (>= 90%%): %.2f%% -- %s\n', branch_passing_frac * 100, branch_label);
fprintf('\n=== RESULT: %s ===\n', overall_status);
fprintf('Wall clock: %.3f seconds\n', solve_time);
fprintf('Peak RSS: %.1f MB\n', rss_after);
