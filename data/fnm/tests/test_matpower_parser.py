"""Tests for the MATPOWER psse2mpc parser wrapper (PRD 01/04).

T01-T08: Synthetic tests (no external dependencies).
T09: Octave integration test (requires Octave + MATPOWER, no FNM).
T10-T13: FNM integration tests (require FNM_PATH, skip if unset).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from fnm.scripts.matpower_parser import (
    MPC_DROPPED_RECORD_TYPES,
    MPC_LOSSY_RECORD_TYPES,
    MatpowerParserLog,
    MatpowerParserSummary,
    ParserWarning,
    build_known_limitations,
    build_octave_command,
    log_to_dict,
    parse_octave_stdout,
    parse_octave_warnings,
    read_csv_field_counts,
    run_psse2mpc,
    summary_to_dict,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_HEADER_LINES = [
    " 0,  100.00, 31.0,  0,  0, 60.00 / PSS/E-31.0 test case",
    "Test case identification line 1",
    "Test case identification line 2",
]


def _make_raw_content(
    header: list[str] | None = None,
    sections: list[list[str]] | None = None,
) -> str:
    """Build a minimal PSS/E v31 RAW file as a string."""
    hdr = header or _VALID_HEADER_LINES
    secs = sections or [[] for _ in range(17)]
    lines = list(hdr)
    for body in secs:
        lines.extend(body)
        lines.append(" 0")
    return "\n".join(lines) + "\n"


def _build_synthetic_raw() -> str:
    """Build a synthetic 3-bus PSS/E v31 RAW file suitable for psse2mpc.

    Contains:
      - 3 buses (slack + PV + PQ)
      - 1 generator on bus 1
      - 2 branches (1-2, 2-3)
      - 1 load on bus 3
      - Remaining sections empty
    """
    bus_data = [
        " 1,'BUS1    ',  138.000,3, 1, 1, 1,1.05000,   0.0000",
        " 2,'BUS2    ',  138.000,2, 1, 1, 1,1.03000,  -2.1000",
        " 3,'BUS3    ',   69.000,1, 1, 1, 1,1.01000,  -5.0000",
    ]
    load_data = [
        " 3,'1 ',1,1,1,   50.000,   25.000,    0.000,    0.000,    0.000,    0.000,1",
    ]
    # Fixed shunt: empty
    gen_data = [
        " 1,'1 ',  100.000,    0.000,  999.000, -999.000,1.05000,0,  200.000,"
        "   0.000,   0.000,   0.000,   0.000,   0.000,   0.000,   0.000,   0.000,"
        "  200.000,   0.000,   1,1.0000,   0,1.0000,   0,1,0,   0.000,   0.000",
    ]
    branch_data = [
        " 1, 2,'1 ', 0.01000, 0.10000, 0.02000, 200.00, 200.00, 200.00,"
        "0.00000,0.00000,0.00000,0.00000,1,1, 0.000, 1, 1,0.0000,   0,   0",
        " 2, 3,'1 ', 0.02000, 0.20000, 0.04000, 100.00, 100.00, 100.00,"
        "0.00000,0.00000,0.00000,0.00000,1,1, 0.000, 1, 1,0.0000,   0,   0",
    ]
    # Sections: Bus, Load, Fixed Shunt, Generator, Branch, Transformer,
    #           Area, Two-Term DC, VSC DC, Imp Corr, MTDC, MSL, Zone,
    #           Interarea, Owner, FACTS, Switched Shunt
    sections: list[list[str]] = [[] for _ in range(17)]
    sections[0] = bus_data
    sections[1] = load_data
    # sections[2] = fixed shunt (empty)
    sections[3] = gen_data
    sections[4] = branch_data
    return _make_raw_content(sections=sections)


# ---------------------------------------------------------------------------
# T01: test_build_octave_command_structure
# ---------------------------------------------------------------------------


def test_build_octave_command_structure() -> None:
    """Verify command list structure from build_octave_command."""
    cmd = build_octave_command("/tmp/test.raw", "/tmp/output")
    assert cmd[0] == "octave"
    assert "--no-gui" in cmd
    assert "--no-init-file" in cmd
    # Script path should end with run_psse2mpc.m
    assert any(arg.endswith("run_psse2mpc.m") for arg in cmd)
    # raw_path and output_dir should be in the command
    assert "/tmp/test.raw" in cmd
    assert "/tmp/output" in cmd


# ---------------------------------------------------------------------------
# T02: test_parse_octave_stdout_valid
# ---------------------------------------------------------------------------


def test_parse_octave_stdout_valid() -> None:
    """Parse synthetic stdout with MPC_BASEMVA, MPC_VERSION, MPC_FIELD_COUNT lines."""
    stdout = (
        "MPC_BASEMVA:100\n"
        "MPC_VERSION:2\n"
        "MPC_FIELD_COUNT:bus:3\n"
        "MPC_FIELD_COUNT:gen:1\n"
        "MPC_FIELD_COUNT:branch:2\n"
        "CONVERSION_COMPLETE\n"
    )
    result = parse_octave_stdout(stdout)
    assert result["_baseMVA"] == 100.0
    assert result["_version"] == "2"
    assert result["bus"] == 3
    assert result["gen"] == 1
    assert result["branch"] == 2


# ---------------------------------------------------------------------------
# T03: test_parse_octave_stdout_empty
# ---------------------------------------------------------------------------


def test_parse_octave_stdout_empty() -> None:
    """Empty string should return empty dict."""
    assert parse_octave_stdout("") == {}
    assert parse_octave_stdout("   \n  \n") == {}


# ---------------------------------------------------------------------------
# T04: test_parse_octave_warnings_classification
# ---------------------------------------------------------------------------


def test_parse_octave_warnings_classification() -> None:
    """Classify warnings as skipped_record, phantom_bus, unsupported_field, conversion_warning."""
    stderr = (
        "PSSE2MPC_WARNING: Skipping Two-Terminal DC records\n"
        "PSSE2MPC_WARNING: Phantom bus 99999 referenced but not in bus table\n"
        "PSSE2MPC_WARNING: Unsupported field type in transformer record\n"
        "PSSE2MPC_WARNING: Some generic conversion issue occurred\n"
        "\n"  # empty line should be skipped
    )
    warnings = parse_octave_warnings(stderr)
    assert len(warnings) == 4
    categories = [w.category for w in warnings]
    assert categories[0] == "skipped_record"
    assert categories[1] == "phantom_bus"
    assert categories[2] == "unsupported_field"
    assert categories[3] == "conversion_warning"


# ---------------------------------------------------------------------------
# T05: test_read_csv_field_counts
# ---------------------------------------------------------------------------


def test_read_csv_field_counts(tmp_path: Path) -> None:
    """Create temp CSVs, verify row counts."""
    # Create synthetic CSV files (no headers, as csvwrite produces)
    (tmp_path / "mpc_bus.csv").write_text("1,138.0,1.05,0\n2,138.0,1.03,-2.1\n3,69.0,1.01,-5.0\n")
    (tmp_path / "mpc_gen.csv").write_text("1,100,0,999,-999\n")
    (tmp_path / "mpc_branch.csv").write_text("1,2,0.01,0.1,0.02\n2,3,0.02,0.2,0.04\n")
    # Non-matching file should be ignored
    (tmp_path / "other.csv").write_text("should,be,ignored\n")

    counts = read_csv_field_counts(tmp_path)
    assert counts["bus"] == 3
    assert counts["gen"] == 1
    assert counts["branch"] == 2
    assert "other" not in counts


# ---------------------------------------------------------------------------
# T06: test_build_known_limitations
# ---------------------------------------------------------------------------


def test_build_known_limitations() -> None:
    """Verify all dropped + lossy record types are covered."""
    limitations = build_known_limitations()
    record_types = {kl.record_type for kl in limitations}

    # All dropped types must be present
    for rt in MPC_DROPPED_RECORD_TYPES:
        assert rt in record_types, f"Missing dropped record type: {rt}"

    # All lossy types must be present
    for rt in MPC_LOSSY_RECORD_TYPES:
        assert rt in record_types, f"Missing lossy record type: {rt}"

    # Verify behaviors
    dropped = {kl.record_type for kl in limitations if kl.behavior == "dropped"}
    lossy = {kl.record_type for kl in limitations if kl.behavior == "lossy"}
    assert dropped == set(MPC_DROPPED_RECORD_TYPES)
    assert lossy == set(MPC_LOSSY_RECORD_TYPES)

    # All must have non-empty descriptions
    for kl in limitations:
        assert kl.description, f"Empty description for {kl.record_type}"


# ---------------------------------------------------------------------------
# T07: test_log_to_dict_json_serializable
# ---------------------------------------------------------------------------


def test_log_to_dict_json_serializable() -> None:
    """Build MatpowerParserLog, convert, json.dumps succeeds."""
    log = MatpowerParserLog(
        raw_path="/tmp/test.raw",
        output_dir="/tmp/output",
        return_code=0,
        stdout="MPC_BASEMVA:100\nMPC_FIELD_COUNT:bus:3\n",
        stderr="PSSE2MPC_WARNING: test warning\n",
        baseMVA=100.0,
        version="2",
        field_counts_octave={"bus": 3},
        field_counts_csv={"bus": 3},
        warnings=[ParserWarning(line="test warning", category="conversion_warning")],
    )
    d = log_to_dict(log)
    json_str = json.dumps(d)
    loaded = json.loads(json_str)
    assert loaded["baseMVA"] == 100.0
    assert loaded["return_code"] == 0
    assert loaded["field_counts_octave"]["bus"] == 3
    assert len(loaded["warnings"]) == 1
    assert loaded["warnings"][0]["category"] == "conversion_warning"


# ---------------------------------------------------------------------------
# T08: test_summary_to_dict_json_serializable
# ---------------------------------------------------------------------------


def test_summary_to_dict_json_serializable() -> None:
    """Build MatpowerParserSummary, convert, json.dumps succeeds."""
    log = MatpowerParserLog(
        raw_path="/tmp/test.raw",
        output_dir="/tmp/output",
        return_code=0,
        stdout="",
        stderr="",
        baseMVA=100.0,
        version="2",
    )
    limitations = build_known_limitations()
    summary = MatpowerParserSummary(
        log=log,
        known_limitations=limitations,
        success=True,
    )
    d = summary_to_dict(summary)
    json_str = json.dumps(d)
    loaded = json.loads(json_str)
    assert loaded["success"] is True
    assert "log" in loaded
    assert "known_limitations" in loaded
    assert len(loaded["known_limitations"]) == len(MPC_DROPPED_RECORD_TYPES) + len(
        MPC_LOSSY_RECORD_TYPES
    )
    # Verify each limitation has required keys
    for kl in loaded["known_limitations"]:
        assert "record_type" in kl
        assert "behavior" in kl
        assert "description" in kl


# ---------------------------------------------------------------------------
# T09: test_run_psse2mpc_synthetic_case (Octave integration)
# ---------------------------------------------------------------------------


@pytest.mark.octave
def test_run_psse2mpc_synthetic_case(tmp_path: Path) -> None:
    """Run psse2mpc on a synthetic PSS/E v31 RAW file.

    Verifies:
      - Return code is 0 (success).
      - Summary has bus/gen/branch counts.
      - CSV files exist in the output directory.
    """
    if shutil.which("octave") is None:
        pytest.skip("Octave not available")

    # Write synthetic RAW file
    raw_content = _build_synthetic_raw()
    raw_path = tmp_path / "synthetic.raw"
    raw_path.write_text(raw_content, encoding="utf-8")

    output_dir = tmp_path / "mpc_output"

    log = run_psse2mpc(raw_path, output_dir, timeout=120)

    # Conversion should succeed
    assert log.return_code == 0, (
        f"psse2mpc failed with return code {log.return_code}.\n"
        f"stdout: {log.stdout}\nstderr: {log.stderr}"
    )

    # Should have baseMVA
    assert log.baseMVA is not None
    assert log.baseMVA == 100.0

    # Should have bus, gen, branch counts from Octave stdout
    assert "bus" in log.field_counts_octave
    assert log.field_counts_octave["bus"] == 3
    assert "gen" in log.field_counts_octave
    assert log.field_counts_octave["gen"] == 1
    assert "branch" in log.field_counts_octave
    assert log.field_counts_octave["branch"] == 2

    # CSV files should exist
    assert (output_dir / "mpc_bus.csv").exists()
    assert (output_dir / "mpc_gen.csv").exists()
    assert (output_dir / "mpc_branch.csv").exists()

    # CSV field counts should match Octave counts
    assert log.field_counts_csv.get("bus") == 3
    assert log.field_counts_csv.get("gen") == 1
    assert log.field_counts_csv.get("branch") == 2


# ---------------------------------------------------------------------------
# FNM integration tests (T10-T13) — require FNM_PATH
# ---------------------------------------------------------------------------


@pytest.mark.fnm
def test_fnm_psse2mpc_converts(require_fnm_raw: Path, tmp_path: Path) -> None:
    """T10: psse2mpc converts the real FNM RAW file without error."""
    if shutil.which("octave") is None:
        pytest.skip("Octave not available")

    output_dir = tmp_path / "fnm_mpc_output"
    log = run_psse2mpc(require_fnm_raw, output_dir, timeout=300)

    assert log.return_code == 0, f"psse2mpc failed on FNM RAW file.\nstderr: {log.stderr[:500]}"
    assert log.baseMVA is not None


@pytest.mark.fnm
def test_fnm_bus_csv_exists(require_fnm_raw: Path, tmp_path: Path) -> None:
    """T11: mpc_bus.csv is produced and has rows in ERCOT-scale range."""
    if shutil.which("octave") is None:
        pytest.skip("Octave not available")

    output_dir = tmp_path / "fnm_mpc_output"
    log = run_psse2mpc(require_fnm_raw, output_dir, timeout=300)

    assert (output_dir / "mpc_bus.csv").exists()
    bus_count = log.field_counts_csv.get("bus", 0)
    assert 25000 <= bus_count <= 35000, f"Bus count {bus_count} outside expected ERCOT range"


@pytest.mark.fnm
def test_fnm_branch_csv_exists(require_fnm_raw: Path, tmp_path: Path) -> None:
    """T12: mpc_branch.csv is produced with a reasonable number of branches."""
    if shutil.which("octave") is None:
        pytest.skip("Octave not available")

    output_dir = tmp_path / "fnm_mpc_output"
    log = run_psse2mpc(require_fnm_raw, output_dir, timeout=300)

    assert (output_dir / "mpc_branch.csv").exists()
    branch_count = log.field_counts_csv.get("branch", 0)
    assert branch_count > 1000, f"Branch count {branch_count} seems too low for ERCOT"


@pytest.mark.fnm
def test_fnm_known_limitations_documented(require_fnm_raw: Path, tmp_path: Path) -> None:
    """T13: Known limitations are documented and summary is JSON-serializable."""
    if shutil.which("octave") is None:
        pytest.skip("Octave not available")

    output_dir = tmp_path / "fnm_mpc_output"
    log = run_psse2mpc(require_fnm_raw, output_dir, timeout=300)
    limitations = build_known_limitations()
    summary = MatpowerParserSummary(
        log=log,
        known_limitations=limitations,
        success=log.return_code == 0,
    )

    d = summary_to_dict(summary)
    json_str = json.dumps(d)
    loaded = json.loads(json_str)
    assert loaded["success"] is True
    assert len(loaded["known_limitations"]) >= 9  # 6 dropped + 3 lossy
