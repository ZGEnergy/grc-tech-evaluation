"""Tests for the PSS/E v31 RAW file record counter (PRD 01/03).

T01-T09: Synthetic tests (no FNM data required).
T10-T12: FNM integration tests (require FNM_PATH, skip if unset).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fnm.scripts.raw_record_counter import (
    PSSE_V31_SECTION_NAMES,
    count_raw_records,
    count_section_records,
    parse_header,
    summary_to_dict,
)

# ---------------------------------------------------------------------------
# Helpers for building synthetic RAW file content
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
    """Build a minimal PSS/E v31 RAW file as a string.

    Args:
        header: 3-line header. Defaults to _VALID_HEADER_LINES.
        sections: A list of 17 section bodies. Each body is a list of data lines
            (the ``0`` sentinel is appended automatically). If a section body is
            empty, only the sentinel line is written. Defaults to 17 empty sections.
    """
    hdr = header or _VALID_HEADER_LINES
    secs = sections or [[] for _ in range(17)]
    lines = list(hdr)
    for body in secs:
        lines.extend(body)
        lines.append(" 0")
    return "\n".join(lines) + "\n"


def _write_raw(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "test.raw"
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# T01: test_parse_header_valid
# ---------------------------------------------------------------------------


def test_parse_header_valid() -> None:
    """Parse a synthetic 3-line v31 header and verify all fields."""
    hdr = parse_header(_VALID_HEADER_LINES)
    assert hdr.ic == 0
    assert hdr.sbase == 100.0
    assert hdr.rev == 31.0
    assert hdr.xfrrat == 0.0
    assert hdr.nxfrat == 0.0
    assert hdr.basfrq == 60.0
    assert hdr.case_id == "Test case identification line 1"
    assert hdr.case_id2 == "Test case identification line 2"


# ---------------------------------------------------------------------------
# T02: test_parse_header_rejects_non_v31
# ---------------------------------------------------------------------------


def test_parse_header_rejects_non_v31() -> None:
    """REV=30.0 should raise ValueError."""
    lines = [
        " 0,  100.00, 30.0,  0,  0, 60.00",
        "Case id 1",
        "Case id 2",
    ]
    with pytest.raises(ValueError, match="v31"):
        parse_header(lines)


# ---------------------------------------------------------------------------
# T03: test_parse_header_rejects_malformed
# ---------------------------------------------------------------------------


def test_parse_header_rejects_malformed() -> None:
    """Non-numeric line 1 should raise ValueError."""
    lines = [
        "this is not a valid header line",
        "Case id 1",
        "Case id 2",
    ]
    with pytest.raises(ValueError, match="[Mm]alformed"):
        parse_header(lines)


# ---------------------------------------------------------------------------
# T04: test_count_section_simple
# ---------------------------------------------------------------------------


def test_count_section_simple() -> None:
    """5 data lines + terminator -> count=5."""
    lines = [
        "1, 'BUS1', 138.0, 1",
        "2, 'BUS2', 138.0, 1",
        "3, 'BUS3', 138.0, 1",
        "4, 'BUS4', 69.0, 1",
        "5, 'BUS5', 69.0, 1",
        " 0",
    ]
    count = count_section_records(iter(lines), section_index=0)
    assert count == 5


# ---------------------------------------------------------------------------
# T05: test_count_section_empty
# ---------------------------------------------------------------------------


def test_count_section_empty() -> None:
    """Just a terminator -> count=0."""
    lines = [" 0"]
    count = count_section_records(iter(lines), section_index=0)
    assert count == 0


# ---------------------------------------------------------------------------
# T06: test_count_section_transformer_2w_and_3w
# ---------------------------------------------------------------------------


def test_count_section_transformer_2w_and_3w() -> None:
    """One 2W (4 lines, K=0) + one 3W (5 lines, K!=0) -> count=2."""
    lines = [
        # 2-winding transformer (K=0): 4 lines
        " 1, 2, 0, '1', 1, 1, 1, 0.0, 0.0, 2, 'xfmr2w'",  # line 1, K=0
        " 0.01, 0.10, 100.0",  # line 2
        " 1.0, 0.0, 0.0, 138.0, 0.0, 0.0, 0, 0, 1.1, 0.9",  # line 3
        " 1.0, 0.0, 0.0, 69.0, 0.0, 0.0",  # line 4
        # 3-winding transformer (K!=0): 5 lines
        " 1, 2, 3, '1', 1, 1, 1, 0.0, 0.0, 2, 'xfmr3w'",  # line 1, K=3
        " 0.01, 0.10, 100.0",  # line 2
        " 1.0, 0.0, 0.0, 138.0, 0.0, 0.0, 0, 0, 1.1, 0.9",  # line 3
        " 1.0, 0.0, 0.0, 69.0, 0.0, 0.0",  # line 4
        " 1.0, 0.0, 0.0, 34.5, 0.0, 0.0",  # line 5
        # sentinel
        " 0",
    ]
    count = count_section_records(iter(lines), section_index=5)
    assert count == 2


# ---------------------------------------------------------------------------
# T07: test_count_section_multi_terminal_dc
# ---------------------------------------------------------------------------


def test_count_section_multi_terminal_dc() -> None:
    """One MTDC record with NCONV=2, NDCBS=3, NDCLN=1 -> count=1."""
    lines = [
        # Main record line: NCONV=2, NDCBS=3, NDCLN=1
        " 2, 3, 1, 'MTDC1', 0",
        # 2 converter lines
        " 1, 100, 1.0, 0.0, 0.0",
        " 2, 200, 1.0, 0.0, 0.0",
        # 3 DC bus lines
        " 1, 1, 100.0, 1, 0",
        " 2, 2, 100.0, 1, 0",
        " 3, 3, 100.0, 1, 0",
        # 1 DC link line
        " 1, 2, '1', 0.01, 100.0",
        # sentinel
        " 0",
    ]
    count = count_section_records(iter(lines), section_index=10)
    assert count == 1


# ---------------------------------------------------------------------------
# T08: test_count_full_synthetic_file
# ---------------------------------------------------------------------------


def test_count_full_synthetic_file(tmp_path: Path) -> None:
    """Full synthetic file: 3 buses, 2 loads, empty rest -> Bus=3, Load=2, total=5."""
    bus_data = [
        " 1, 'BUS1    ', 138.0, 1, 1, 1, 1, 1.05, 0.0",
        " 2, 'BUS2    ', 138.0, 1, 1, 1, 1, 1.03, -2.1",
        " 3, 'BUS3    ', 69.0, 1, 1, 1, 1, 1.01, -5.0",
    ]
    load_data = [
        " 1, '1', 1, 1, 1, 50.0, 25.0, 0.0, 0.0, 0.0, 0.0, 1",
        " 2, '1', 1, 1, 1, 100.0, 50.0, 0.0, 0.0, 0.0, 0.0, 1",
    ]
    sections: list[list[str]] = [[] for _ in range(17)]
    sections[0] = bus_data
    sections[1] = load_data

    content = _make_raw_content(sections=sections)
    raw_path = _write_raw(tmp_path, content)

    summary = count_raw_records(raw_path)
    assert summary.section_counts["Bus"] == 3
    assert summary.section_counts["Load"] == 2
    assert summary.total_data_lines == 5
    assert summary.header.rev == 31.0
    assert len(summary.section_counts) == 17
    # All other sections should be 0
    for name in PSSE_V31_SECTION_NAMES[2:]:
        assert summary.section_counts[name] == 0


# ---------------------------------------------------------------------------
# T09: test_summary_to_dict_roundtrip
# ---------------------------------------------------------------------------


def test_summary_to_dict_roundtrip(tmp_path: Path) -> None:
    """Build summary, convert to dict, verify JSON-serializable."""
    content = _make_raw_content()
    raw_path = _write_raw(tmp_path, content)
    summary = count_raw_records(raw_path)

    d = summary_to_dict(summary)

    # Must be JSON-serializable
    json_str = json.dumps(d)
    loaded = json.loads(json_str)

    assert loaded["header"]["rev"] == 31.0
    assert loaded["total_sections"] == 17
    assert isinstance(loaded["section_counts"], dict)
    assert len(loaded["section_counts"]) == 17
    assert isinstance(loaded["hvdc_facts_present"], dict)
    assert set(loaded["hvdc_facts_present"].keys()) == {
        "Two-Terminal DC",
        "VSC DC",
        "Multi-Terminal DC",
        "FACTS",
    }


# ---------------------------------------------------------------------------
# FNM integration tests (T10-T12) — require FNM_PATH
# ---------------------------------------------------------------------------


@pytest.mark.fnm
def test_fnm_header_is_v31(require_fnm_raw: Path) -> None:
    """T10: FNM header is v31 with sbase=100.0."""
    summary = count_raw_records(require_fnm_raw)
    assert summary.header.rev == 31.0
    assert summary.header.sbase == 100.0


@pytest.mark.fnm
def test_fnm_bus_count_scale(require_fnm_raw: Path) -> None:
    """T11: Bus count in 25000-35000 range (ERCOT-scale network)."""
    summary = count_raw_records(require_fnm_raw)
    assert 25000 <= summary.section_counts["Bus"] <= 35000, (
        f"Bus count {summary.section_counts['Bus']} outside expected ERCOT range"
    )


@pytest.mark.fnm
def test_fnm_all_17_sections_present(require_fnm_raw: Path) -> None:
    """T12: All 17 sections present in section_counts, total_sections==17."""
    summary = count_raw_records(require_fnm_raw)
    assert summary.total_sections == 17
    assert set(summary.section_counts.keys()) == set(PSSE_V31_SECTION_NAMES)
