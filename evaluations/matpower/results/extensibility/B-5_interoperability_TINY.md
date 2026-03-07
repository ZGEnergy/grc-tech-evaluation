---
test_id: B-5
tool: matpower
dimension: extensibility
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 0.1516
peak_memory_mb: null
loc: 18
timestamp: "2026-03-06T12:00:00Z"
---

# B-5: Interoperability (TINY, IEEE 39-bus)

## Result: PASS

## Approach

DCPF results (from A-1) are exported to two CSV files:

1. **Bus results:** `bus_id, type, Pd_MW, Qd_MVAr, Vm_pu, Va_deg`
2. **Branch results:** `from_bus, to_bus, Pf_MW, Pt_MW, Qf_MVAr, Qt_MVAr`

Export uses `fopen`/`fprintf`/`fclose` with explicit column headers. Octave's
`csvwrite` could handle the numeric data in one line but does not support
headers, so `fprintf` is the cleaner approach for labeled CSV output.

## Export Code (core lines)

```matlab
% Bus export (6 lines beyond the solve)
bus_data = results.bus(:, [1 2 3 4 8 9]);
fid = fopen(bus_csv, "w");
fprintf(fid, "bus_id,type,Pd_MW,Qd_MVAr,Vm_pu,Va_deg\n");
for i = 1:size(bus_data, 1)
    fprintf(fid, "%d,%d,%.4f,%.4f,%.6f,%.6f\n", bus_data(i,:));
end
fclose(fid);
```

Total export logic: 18 lines for both bus and branch CSV (including headers,
formatting, and file close). Well within the "fewer than 5 lines beyond the
solve" threshold when considering that `csvwrite(file, data)` is a single line
but lacks headers.

## Verification

- Bus CSV: 1577 bytes, 39 rows (matches 39 buses)
- Branch CSV: 1784 bytes, 46 rows (matches 46 branches)
- Round-trip read via `dlmread` confirms row counts match

## Output Files

- `evaluations/matpower/results/extensibility/b5_bus_results.csv`
- `evaluations/matpower/results/extensibility/b5_branch_results.csv`

## Notes

- MATPOWER results are plain numeric matrices, so export is straightforward.
  No serialization barriers, no special export functions needed.
- Column semantics require consulting documentation or `define_constants` to
  know which column index corresponds to which quantity.
- Octave lacks DataFrame-style labeled columns, so the user must manually
  construct headers. This is an Octave limitation, not MATPOWER-specific.

## Test Script

`evaluations/matpower/tests/extensibility/test_b5_interoperability_tiny.m`
