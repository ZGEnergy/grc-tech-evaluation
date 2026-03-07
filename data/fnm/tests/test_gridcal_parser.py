"""Tests for GridCal v31 parser module.

T01-T07: Synthetic tests that validate data structures and constants without GridCal.
T08-T09: Integration tests requiring GridCal (skip if not installed).
T10-T12: FNM integration tests requiring both GridCal and FNM_PATH.
"""

from __future__ import annotations

import json

import pytest

from fnm.scripts.gridcal_parser import (
    GRIDCAL_ELEMENT_COLLECTIONS,
    PSSE_TO_GRIDCAL_MAPPING,
    GridCalParserSummary,
    MultiCircuitCounts,
    ParserLog,
    ParserLogEntry,
    PsseIntermediateCounts,
    build_record_type_mapping,
    parser_log_to_dict,
    summary_to_dict,
)
from fnm.scripts.raw_record_counter import PSSE_V31_SECTION_NAMES

# ---------------------------------------------------------------------------
# Synthetic tests (T01-T07) — no GridCal needed
# ---------------------------------------------------------------------------


class TestPsseToGridcalMapping:
    """T01: Verify PSSE_TO_GRIDCAL_MAPPING covers all 17 PSS/E sections."""

    def test_psse_to_gridcal_mapping_covers_all_17_sections(self) -> None:
        assert len(PSSE_TO_GRIDCAL_MAPPING) == 17
        for section_name in PSSE_V31_SECTION_NAMES:
            assert section_name in PSSE_TO_GRIDCAL_MAPPING, (
                f"Missing mapping for PSS/E section: {section_name}"
            )


class TestBuildRecordTypeMapping:
    """T02-T04: Verify build_record_type_mapping output."""

    def test_build_record_type_mapping_all_sections(self) -> None:
        """T02: 17 entries, each with valid status and non-empty notes."""
        mappings = build_record_type_mapping()
        assert len(mappings) == 17

        valid_statuses = {"mapped", "dropped", "merged"}
        for m in mappings:
            assert m.status in valid_statuses, (
                f"Invalid status '{m.status}' for section '{m.psse_section}'"
            )
            assert m.notes, f"Empty notes for section '{m.psse_section}'"
            assert m.psse_section in PSSE_V31_SECTION_NAMES

    def test_build_record_type_mapping_dropped_sections(self) -> None:
        """T03: Multi-Terminal DC, Multi-Section Line, Interarea Transfer, Owner are dropped."""
        mappings = build_record_type_mapping()
        mapping_by_section = {m.psse_section: m for m in mappings}

        dropped_sections = [
            "Multi-Terminal DC",
            "Multi-Section Line",
            "Interarea Transfer",
            "Owner",
        ]
        for section_name in dropped_sections:
            m = mapping_by_section[section_name]
            assert m.status == "dropped", (
                f"Expected 'dropped' for '{section_name}', got '{m.status}'"
            )
            assert m.gridcal_collection is None

    def test_build_record_type_mapping_merged_sections(self) -> None:
        """T04: Impedance Correction has status='merged'."""
        mappings = build_record_type_mapping()
        mapping_by_section = {m.psse_section: m for m in mappings}

        m = mapping_by_section["Impedance Correction"]
        assert m.status == "merged"
        assert m.gridcal_collection is None


class TestSummaryRoundtrip:
    """T05: Build GridCalParserSummary with synthetic data, json.dumps succeeds."""

    def test_summary_to_dict_roundtrip(self) -> None:
        summary = GridCalParserSummary(
            raw_path="/fake/path/test.raw",
            psse_intermediate_counts=PsseIntermediateCounts(bus=100, load=50, generator=10),
            multicircuit_counts=MultiCircuitCounts(buses=100, loads=50, generators=10),
            parser_log=ParserLog(
                entries=[
                    ParserLogEntry(
                        time="2025-01-01T00:00:00Z",
                        severity="INFO",
                        message="Test message",
                    )
                ],
                info_count=1,
                warning_count=0,
                error_count=0,
            ),
            record_type_mapping=build_record_type_mapping(),
            csv_files=["/fake/output/gridcal_buses.csv"],
            log_file="/fake/output/parser_log.json",
            timestamp="2025-01-01T00:00:00Z",
        )

        result = summary_to_dict(summary)

        # Must be JSON-serializable
        json_str = json.dumps(result)
        assert json_str

        # Roundtrip: parse back and verify key fields
        parsed = json.loads(json_str)
        assert parsed["raw_path"] == "/fake/path/test.raw"
        assert parsed["psse_intermediate_counts"]["bus"] == 100
        assert parsed["multicircuit_counts"]["buses"] == 100
        assert len(parsed["record_type_mapping"]) == 17
        assert parsed["csv_files"] == ["/fake/output/gridcal_buses.csv"]


class TestParserLogToDict:
    """T06: Verify parser_log_to_dict structure with 3 synthetic entries."""

    def test_parser_log_to_dict_structure(self) -> None:
        log = ParserLog(
            entries=[
                ParserLogEntry(
                    time="2025-01-01T00:00:00Z",
                    severity="INFO",
                    message="Info message",
                ),
                ParserLogEntry(
                    time="2025-01-01T00:00:01Z",
                    severity="WARNING",
                    message="Warning message",
                    device="BUS-1",
                ),
                ParserLogEntry(
                    time="2025-01-01T00:00:02Z",
                    severity="ERROR",
                    message="Error message",
                    device="GEN-1",
                    device_class="Generator",
                ),
            ],
            info_count=1,
            warning_count=1,
            error_count=1,
        )

        result = parser_log_to_dict(log)

        assert len(result["entries"]) == 3
        assert result["info_count"] == 1
        assert result["warning_count"] == 1
        assert result["error_count"] == 1

        # Verify entry structure
        entry0 = result["entries"][0]
        assert "time" in entry0
        assert "severity" in entry0
        assert "message" in entry0
        assert "device" in entry0
        assert "device_class" in entry0

        # Must be JSON-serializable
        json_str = json.dumps(result)
        assert json_str


class TestGridCalElementCollections:
    """T07: Verify GRIDCAL_ELEMENT_COLLECTIONS is non-empty and valid."""

    def test_gridcal_element_collections_tuple_not_empty(self) -> None:
        assert isinstance(GRIDCAL_ELEMENT_COLLECTIONS, tuple)
        assert len(GRIDCAL_ELEMENT_COLLECTIONS) > 0

        for name in GRIDCAL_ELEMENT_COLLECTIONS:
            assert isinstance(name, str)
            assert name.isidentifier(), f"'{name}' is not a valid Python identifier"


# ---------------------------------------------------------------------------
# GridCal integration tests (T08-T09) — require GridCal, no FNM
# ---------------------------------------------------------------------------


@pytest.mark.gridcal
class TestGridCalCase39:
    """T08-T09: Integration tests loading case39.m via GridCal."""

    def test_load_case39_produces_multicircuit(self, require_gridcal, tmp_path) -> None:
        """T08: Load case39.m, verify it produces a MultiCircuit with buses."""
        from fnm.scripts.gridcal_parser import count_multicircuit, load_raw_with_logging

        case39_path = require_gridcal["case39_path"]
        grid, _psse_circuit, _logger = load_raw_with_logging(case39_path)

        counts = count_multicircuit(grid)
        # IEEE 39-bus system should have 39 buses
        assert counts.buses == 39, f"Expected 39 buses, got {counts.buses}"

    def test_export_case39_csv_tables(self, require_gridcal, tmp_path) -> None:
        """T09: Export collections to tmp_path, verify CSV files exist."""
        from fnm.scripts.gridcal_parser import export_all_collections, load_raw_with_logging

        case39_path = require_gridcal["case39_path"]
        grid, _psse_circuit, _logger = load_raw_with_logging(case39_path)

        csv_files = export_all_collections(grid, tmp_path)
        assert len(csv_files) > 0, "Expected at least one CSV file exported"

        for csv_path in csv_files:
            assert csv_path.exists(), f"CSV file not found: {csv_path}"
            assert csv_path.stat().st_size > 0, f"CSV file is empty: {csv_path}"


# ---------------------------------------------------------------------------
# FNM integration tests (T10-T12) — require FNM_PATH + GridCal
# ---------------------------------------------------------------------------


@pytest.mark.fnm
@pytest.mark.gridcal
class TestGridCalFnm:
    """T10-T12: FNM integration tests requiring both GridCal and FNM_PATH."""

    def test_load_fnm_raw_produces_multicircuit(self, require_gridcal, require_fnm_raw) -> None:
        """T10: Load the ERCOT FNM RAW file, verify non-zero bus count."""
        from fnm.scripts.gridcal_parser import count_multicircuit, load_raw_with_logging

        grid, _psse_circuit, _logger = load_raw_with_logging(require_fnm_raw)
        counts = count_multicircuit(grid)
        assert counts.buses > 0, "Expected non-zero bus count from FNM RAW"

    def test_export_fnm_csv_tables(self, require_gridcal, require_fnm_raw, tmp_path) -> None:
        """T11: Export FNM collections to CSV, verify multiple files."""
        from fnm.scripts.gridcal_parser import export_all_collections, load_raw_with_logging

        grid, _psse_circuit, _logger = load_raw_with_logging(require_fnm_raw)
        csv_files = export_all_collections(grid, tmp_path)
        assert len(csv_files) >= 5, f"Expected at least 5 CSV files from FNM, got {len(csv_files)}"

    def test_fnm_parser_log_captured(self, require_gridcal, require_fnm_raw) -> None:
        """T12: Verify parser log is captured during FNM parsing."""
        from fnm.scripts.gridcal_parser import extract_logger_entries, load_raw_with_logging

        _grid, _psse_circuit, logger = load_raw_with_logging(require_fnm_raw)
        parser_log = extract_logger_entries(logger)

        # The log object should be valid even if empty
        assert isinstance(parser_log.entries, list)
        total = parser_log.info_count + parser_log.warning_count + parser_log.error_count
        assert total == len(parser_log.entries)
