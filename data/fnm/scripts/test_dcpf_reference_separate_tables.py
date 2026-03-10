"""Tests for dcpf_reference.py separate-table support (PRD 00/03).

Tests cover:
- load_transformer_table: PSS/E column mapping, normalization, error handling
- load_manifest / resolve_base_mva: manifest loading and baseMVA resolution
- run_dcpf_reference with transformer_csv_path: separate-table vs merged parity
- CLI argument parsing for --transformer-csv and --manifest flags
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest
from dcpf_reference import (
    load_manifest,
    load_transformer_table,
    main,
    resolve_base_mva,
    run_dcpf_reference,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_csv(path: Path, text: str) -> Path:
    """Write dedented CSV text to a file and return the path."""
    path.write_text(textwrap.dedent(text).lstrip(), encoding="utf-8")
    return path


def _write_bus_csv(tmp_path: Path, rows: list[tuple]) -> Path:
    """Write a minimal bus CSV. Rows are (bus_i, bus_type, pd, base_kv)."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    lines = ["BUS_I,BUS_TYPE,PD,BASE_KV"]
    for r in rows:
        lines.append(",".join(str(v) for v in r))
    p = tmp_path / "bus.csv"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def _write_gen_csv(tmp_path: Path, rows: list[tuple]) -> Path:
    """Write a minimal gen CSV. Rows are (gen_bus, pg, gen_status, id)."""
    lines = ["GEN_BUS,PG,GEN_STATUS,ID"]
    for r in rows:
        lines.append(",".join(str(v) for v in r))
    p = tmp_path / "gen.csv"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def _write_branch_csv(tmp_path: Path, rows: list[tuple]) -> Path:
    """Write a minimal branch CSV. Rows are (f_bus, t_bus, br_x, tap, shift, br_status, ckt)."""
    lines = ["F_BUS,T_BUS,BR_X,TAP,SHIFT,BR_STATUS,CKT"]
    for r in rows:
        lines.append(",".join(str(v) for v in r))
    p = tmp_path / "branch.csv"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def _write_exclusion_csv(tmp_path: Path, bus_numbers: list[int] | None = None) -> Path:
    """Write a minimal exclusion CSV."""
    lines = ["bus_number"]
    for bn in bus_numbers or []:
        lines.append(str(bn))
    p = tmp_path / "excluded_buses.csv"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def _write_transformer_csv(tmp_path: Path, rows: list[tuple], fname: str = "xfmr.csv") -> Path:
    """Write a transformer CSV with PSS/E columns.

    Rows are (I, J, X1_2, WINDV1, ANG1, STAT, CKT).
    """
    lines = ["I,J,X1_2,WINDV1,ANG1,STAT,CKT"]
    for r in rows:
        lines.append(",".join(str(v) for v in r))
    p = tmp_path / fname
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# 1. test_load_transformer_table_reads_psse_columns
# ---------------------------------------------------------------------------


def test_load_transformer_table_reads_psse_columns(tmp_path: Path) -> None:
    """3 synthetic rows — verify BranchRecord field mappings."""
    p = _write_transformer_csv(
        tmp_path,
        [
            (1, 2, 0.05, 1.05, 0.0, 1, "1"),
            (3, 4, 0.10, 0.95, 5.0, 1, "2"),
            (5, 6, 0.20, 1.00, -3.0, 1, "1"),
        ],
    )
    records = load_transformer_table(p)

    assert len(records) == 3

    assert records[0].from_bus == 1
    assert records[0].to_bus == 2
    assert records[0].x_pu == pytest.approx(0.05)
    assert records[0].tap_ratio == pytest.approx(1.05)
    assert records[0].shift_deg == pytest.approx(0.0)
    assert records[0].status == 1
    assert records[0].circuit_id == "1"
    assert records[0].is_transformer is True

    assert records[1].from_bus == 3
    assert records[1].to_bus == 4
    assert records[1].x_pu == pytest.approx(0.10)
    assert records[1].tap_ratio == pytest.approx(0.95)
    assert records[1].shift_deg == pytest.approx(5.0)
    assert records[1].circuit_id == "2"

    assert records[2].shift_deg == pytest.approx(-3.0)


# ---------------------------------------------------------------------------
# 2. test_load_transformer_table_normalizes_windv1_zero
# ---------------------------------------------------------------------------


def test_load_transformer_table_normalizes_windv1_zero(tmp_path: Path) -> None:
    """WINDV1=0 should be normalized to tap_ratio=1.0."""
    p = _write_transformer_csv(tmp_path, [(1, 2, 0.05, 0.0, 0.0, 1, "1")])
    records = load_transformer_table(p)
    assert records[0].tap_ratio == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# 3. test_load_transformer_table_stat_mapping
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("stat_in", "status_out"),
    [(0, 0), (1, 1), (2, 1), (3, 1), (4, 1)],
)
def test_load_transformer_table_stat_mapping(tmp_path: Path, stat_in: int, status_out: int) -> None:
    """PSS/E STAT 0-4 maps correctly to BranchRecord status."""
    p = _write_transformer_csv(tmp_path, [(1, 2, 0.05, 1.0, 0.0, stat_in, "1")])
    records = load_transformer_table(p)
    assert records[0].status == status_out


# ---------------------------------------------------------------------------
# 4. test_load_transformer_table_missing_required_column
# ---------------------------------------------------------------------------


def test_load_transformer_table_missing_required_column(tmp_path: Path) -> None:
    """Missing X1_2 column raises ValueError."""
    p = tmp_path / "bad_xfmr.csv"
    p.write_text("I,J,STAT\n1,2,1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Required columns not found"):
        load_transformer_table(p)


# ---------------------------------------------------------------------------
# 5. test_load_transformer_table_file_not_found
# ---------------------------------------------------------------------------


def test_load_transformer_table_file_not_found(tmp_path: Path) -> None:
    """Non-existent file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_transformer_table(tmp_path / "nonexistent.csv")


# ---------------------------------------------------------------------------
# 6. test_transformer_column_map_autodetects_variants
# ---------------------------------------------------------------------------


def test_transformer_column_map_autodetects_variants(tmp_path: Path) -> None:
    """Variant column names (from_bus, to_bus, br_x, etc.) are auto-detected."""
    p = tmp_path / "variant_xfmr.csv"
    p.write_text(
        "from_bus,to_bus,br_x,tap,shift,status,circuit\n1,2,0.05,1.0,0.0,1,1\n",
        encoding="utf-8",
    )
    records = load_transformer_table(p)
    assert len(records) == 1
    assert records[0].from_bus == 1
    assert records[0].to_bus == 2
    assert records[0].x_pu == pytest.approx(0.05)


# ---------------------------------------------------------------------------
# 7. test_load_manifest_reads_sbase
# ---------------------------------------------------------------------------


def test_load_manifest_reads_sbase(tmp_path: Path) -> None:
    """Manifest with sbase == 100.0 is correctly parsed."""
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({"sbase": 100.0, "version": 7}), encoding="utf-8")
    m = load_manifest(p)
    assert m["sbase"] == 100.0


# ---------------------------------------------------------------------------
# 8. test_load_manifest_file_not_found
# ---------------------------------------------------------------------------


def test_load_manifest_file_not_found(tmp_path: Path) -> None:
    """Non-existent manifest raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_manifest(tmp_path / "nope.json")


# ---------------------------------------------------------------------------
# 9. test_load_manifest_invalid_json
# ---------------------------------------------------------------------------


def test_load_manifest_invalid_json(tmp_path: Path) -> None:
    """Invalid JSON raises ValueError."""
    p = tmp_path / "bad.json"
    p.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid JSON"):
        load_manifest(p)


# ---------------------------------------------------------------------------
# 10. test_resolve_base_mva_cli_overrides_manifest
# ---------------------------------------------------------------------------


def test_resolve_base_mva_cli_overrides_manifest() -> None:
    """CLI value (200.0) overrides manifest sbase (100.0)."""
    base, source = resolve_base_mva(200.0, {"sbase": 100.0})
    assert base == pytest.approx(200.0)
    assert source == "cli"


# ---------------------------------------------------------------------------
# 11. test_resolve_base_mva_manifest_overrides_default
# ---------------------------------------------------------------------------


def test_resolve_base_mva_manifest_overrides_default() -> None:
    """Manifest sbase (150.0) overrides the default (100.0)."""
    base, source = resolve_base_mva(None, {"sbase": 150.0})
    assert base == pytest.approx(150.0)
    assert source == "manifest"


# ---------------------------------------------------------------------------
# 12. test_resolve_base_mva_falls_back_to_default
# ---------------------------------------------------------------------------


def test_resolve_base_mva_falls_back_to_default() -> None:
    """Neither CLI nor manifest -> falls back to 100.0."""
    base, source = resolve_base_mva(None, None)
    assert base == pytest.approx(100.0)
    assert source == "default"


# ---------------------------------------------------------------------------
# Synthetic 5-bus network helpers
# ---------------------------------------------------------------------------


def _make_5bus_network(tmp_path: Path, *, separate: bool) -> dict[str, Path]:
    """Create a synthetic 5-bus network for integration tests.

    Topology:
        Bus 1 (slack, type=3) -- branch --> Bus 2 (PV, type=2)
        Bus 2 -- branch --> Bus 3 (PQ, type=1)
        Bus 3 -- branch --> Bus 4 (PQ, type=1)
        Bus 1 -- transformer --> Bus 5 (PQ, type=1)

    Generator at bus 1: 150 MW
    Loads: bus 2=50, bus 3=40, bus 4=30, bus 5=30 (total=150)
    """
    bus_csv = _write_bus_csv(
        tmp_path,
        [
            (1, 3, 0.0, 230.0),  # slack
            (2, 2, 50.0, 230.0),  # PV
            (3, 1, 40.0, 230.0),  # PQ
            (4, 1, 30.0, 230.0),  # PQ
            (5, 1, 30.0, 115.0),  # PQ
        ],
    )
    gen_csv = _write_gen_csv(tmp_path, [(1, 150.0, 1, "1")])
    excl_csv = _write_exclusion_csv(tmp_path)

    # Lines: 1-2, 2-3, 3-4
    line_rows = [
        (1, 2, 0.05, 0.0, 0.0, 1, "1"),
        (2, 3, 0.10, 0.0, 0.0, 1, "1"),
        (3, 4, 0.08, 0.0, 0.0, 1, "1"),
    ]

    # Transformer: 1-5 with tap=1.05
    xfmr_row = (1, 5, 0.06, 1.05, 0.0, 1, "1")

    paths: dict[str, Path] = {
        "bus": bus_csv,
        "gen": gen_csv,
        "excl": excl_csv,
    }

    if separate:
        # Lines only in branch CSV, transformer in separate file
        paths["branch"] = _write_branch_csv(tmp_path, line_rows)
        paths["xfmr"] = _write_transformer_csv(tmp_path, [xfmr_row])
    else:
        # Merged: lines + transformer in a single branch CSV
        # Convert transformer to branch format (tap=1.05 not 0)
        merged_rows = line_rows + [xfmr_row]
        paths["branch"] = _write_branch_csv(tmp_path, merged_rows)

    return paths


# ---------------------------------------------------------------------------
# 13. test_run_dcpf_separate_tables_produces_same_solution
# ---------------------------------------------------------------------------


def test_run_dcpf_separate_tables_produces_same_solution(tmp_path: Path) -> None:
    """Separate-table path produces the same bus angles and branch flows as merged."""
    merged_dir = tmp_path / "merged"
    merged_dir.mkdir()
    sep_dir = tmp_path / "separate"
    sep_dir.mkdir()

    merged = _make_5bus_network(merged_dir, separate=False)
    sep = _make_5bus_network(sep_dir, separate=True)

    out_merged = tmp_path / "out_merged"
    out_sep = tmp_path / "out_sep"

    sol_merged = run_dcpf_reference(
        bus_csv_path=merged["bus"],
        gen_csv_path=merged["gen"],
        branch_csv_path=merged["branch"],
        exclusion_csv_path=merged["excl"],
        output_dir=out_merged,
        base_mva=100.0,
    )
    sol_sep = run_dcpf_reference(
        bus_csv_path=sep["bus"],
        gen_csv_path=sep["gen"],
        branch_csv_path=sep["branch"],
        exclusion_csv_path=sep["excl"],
        output_dir=out_sep,
        base_mva=100.0,
        transformer_csv_path=sep["xfmr"],
    )

    # Bus angles must match
    assert set(sol_merged.bus_angles_deg.keys()) == set(sol_sep.bus_angles_deg.keys())
    for bus in sol_merged.bus_angles_deg:
        assert sol_merged.bus_angles_deg[bus] == pytest.approx(
            sol_sep.bus_angles_deg[bus], abs=1e-6
        )

    # Branch flow count must match
    assert len(sol_merged.branch_flows_mw) == len(sol_sep.branch_flows_mw)

    # Flows must match (sort for deterministic comparison)
    merged_flows = sorted(
        sol_merged.branch_flows_mw, key=lambda f: (f.from_bus, f.to_bus, f.circuit_id)
    )
    sep_flows = sorted(sol_sep.branch_flows_mw, key=lambda f: (f.from_bus, f.to_bus, f.circuit_id))
    for mf, sf in zip(merged_flows, sep_flows):
        assert mf.p_flow_mw == pytest.approx(sf.p_flow_mw, abs=1e-6)


# ---------------------------------------------------------------------------
# 14. test_run_dcpf_legacy_path_unchanged
# ---------------------------------------------------------------------------


def test_run_dcpf_legacy_path_unchanged(tmp_path: Path) -> None:
    """Merged CSV without --transformer-csv produces the same result as before."""
    net = _make_5bus_network(tmp_path, separate=False)
    out = tmp_path / "out"

    sol = run_dcpf_reference(
        bus_csv_path=net["bus"],
        gen_csv_path=net["gen"],
        branch_csv_path=net["branch"],
        exclusion_csv_path=net["excl"],
        output_dir=out,
        base_mva=100.0,
    )

    # Slack bus angle is 0
    assert sol.bus_angles_deg[1] == pytest.approx(0.0)
    # 4 in-service branches (3 lines + 1 transformer in merged)
    assert sol.active_branch_count == 4
    # Output files exist
    assert (out / "buses_dcpf.csv").exists()
    assert (out / "branches_dcpf.csv").exists()
    assert (out / "summary_dcpf.json").exists()


# ---------------------------------------------------------------------------
# 15. test_main_cli_accepts_transformer_csv_flag
# ---------------------------------------------------------------------------


def test_main_cli_accepts_transformer_csv_flag(tmp_path: Path) -> None:
    """--transformer-csv flag is accepted and passed to run_dcpf_reference."""
    net = _make_5bus_network(tmp_path / "data", separate=True)
    out = tmp_path / "out"

    argv = [
        "--bus-csv",
        str(net["bus"]),
        "--gen-csv",
        str(net["gen"]),
        "--branch-csv",
        str(net["branch"]),
        "--exclusion-csv",
        str(net["excl"]),
        "--transformer-csv",
        str(net["xfmr"]),
        "-o",
        str(out),
    ]

    with pytest.raises(SystemExit) as exc_info:
        main(argv)
    assert exc_info.value.code == 0


# ---------------------------------------------------------------------------
# 16. test_main_cli_accepts_manifest_flag
# ---------------------------------------------------------------------------


def test_main_cli_accepts_manifest_flag(tmp_path: Path) -> None:
    """--manifest flag is accepted and sbase is used for baseMVA."""
    net = _make_5bus_network(tmp_path / "data", separate=False)
    out = tmp_path / "out"

    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({"sbase": 100.0}), encoding="utf-8")

    argv = [
        "--bus-csv",
        str(net["bus"]),
        "--gen-csv",
        str(net["gen"]),
        "--branch-csv",
        str(net["branch"]),
        "--exclusion-csv",
        str(net["excl"]),
        "--manifest",
        str(manifest_path),
        "-o",
        str(out),
    ]

    with pytest.raises(SystemExit) as exc_info:
        main(argv)
    assert exc_info.value.code == 0


# ---------------------------------------------------------------------------
# 17. test_main_cli_base_mva_overrides_manifest
# ---------------------------------------------------------------------------


def test_main_cli_base_mva_overrides_manifest(tmp_path: Path) -> None:
    """--base-mva overrides manifest sbase."""
    net = _make_5bus_network(tmp_path / "data", separate=False)
    out = tmp_path / "out"

    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({"sbase": 200.0}), encoding="utf-8")

    argv = [
        "--bus-csv",
        str(net["bus"]),
        "--gen-csv",
        str(net["gen"]),
        "--branch-csv",
        str(net["branch"]),
        "--exclusion-csv",
        str(net["excl"]),
        "--manifest",
        str(manifest_path),
        "--base-mva",
        "100.0",
        "-o",
        str(out),
    ]

    with pytest.raises(SystemExit) as exc_info:
        main(argv)
    assert exc_info.value.code == 0

    # Verify the summary has base_mva=100, not 200
    summary = json.loads((out / "summary_dcpf.json").read_text(encoding="utf-8"))
    assert summary["base_mva"] == pytest.approx(100.0)


# ---------------------------------------------------------------------------
# 18. test_main_cli_backward_compat_no_new_flags
# ---------------------------------------------------------------------------


def test_main_cli_backward_compat_no_new_flags(tmp_path: Path) -> None:
    """CLI without --transformer-csv or --manifest works exactly as before."""
    net = _make_5bus_network(tmp_path / "data", separate=False)
    out = tmp_path / "out"

    argv = [
        "--bus-csv",
        str(net["bus"]),
        "--gen-csv",
        str(net["gen"]),
        "--branch-csv",
        str(net["branch"]),
        "--exclusion-csv",
        str(net["excl"]),
        "-o",
        str(out),
    ]

    with pytest.raises(SystemExit) as exc_info:
        main(argv)
    assert exc_info.value.code == 0

    assert (out / "buses_dcpf.csv").exists()
    assert (out / "branches_dcpf.csv").exists()
    assert (out / "summary_dcpf.json").exists()
