"""Parser-independent PSS/E v31 RAW file record counter.

Reads a PSS/E v31 RAW file and counts data records per section by pure text/line
parsing. Understands the v31 file structure: 3-line header followed by 17 record
sections each terminated by a ``0`` sentinel line.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

PSSE_V31_SECTION_NAMES: tuple[str, ...] = (
    "Bus",
    "Load",
    "Fixed Shunt",
    "Generator",
    "Branch",
    "Transformer",
    "Area",
    "Two-Terminal DC",
    "VSC DC",
    "Impedance Correction",
    "Multi-Terminal DC",
    "Multi-Section Line",
    "Zone",
    "Interarea Transfer",
    "Owner",
    "FACTS",
    "Switched Shunt",
)

_HVDC_FACTS_KEYS = ("Two-Terminal DC", "VSC DC", "Multi-Terminal DC", "FACTS")


@dataclass(frozen=True)
class HeaderInfo:
    """Parsed PSS/E v31 3-line header."""

    ic: int
    sbase: float
    rev: float
    xfrrat: float
    nxfrat: float
    basfrq: float
    case_id: str
    case_id2: str


@dataclass(frozen=True)
class RecordCountSummary:
    """Summary of record counts across all 17 PSS/E v31 sections."""

    header: HeaderInfo
    section_counts: dict[str, int]
    total_data_lines: int
    non_empty_sections: list[str]
    total_sections: int
    hvdc_facts_present: dict[str, bool]


def _is_sentinel(line: str) -> bool:
    """Check if a line is a section-terminating sentinel (first token is '0')."""
    stripped = line.strip()
    if not stripped:
        return False
    first_token = stripped.split()[0]
    # Also handle comma-separated: "0," or "0 ,"
    return first_token.rstrip(",") == "0"


def parse_header(lines: list[str]) -> HeaderInfo:
    """Parse 3-line PSS/E v31 header.

    Args:
        lines: The first 3 lines of the RAW file.

    Returns:
        Parsed HeaderInfo.

    Raises:
        ValueError: If the header is malformed or not v31.
    """
    if len(lines) < 3:
        raise ValueError(f"Expected at least 3 header lines, got {len(lines)}")

    # Line 1: IC, SBASE, REV, XFRRAT, NXFRAT, BASFRQ  / comment
    line1 = lines[0].split("/")[0].strip()
    parts = [p.strip() for p in line1.split(",") if p.strip()]

    try:
        ic = int(float(parts[0]))
        sbase = float(parts[1])
        rev = float(parts[2]) if len(parts) > 2 else 0.0
        xfrrat = float(parts[3]) if len(parts) > 3 else 0.0
        nxfrat = float(parts[4]) if len(parts) > 4 else 0.0
        basfrq = float(parts[5]) if len(parts) > 5 else 0.0
    except (ValueError, IndexError) as exc:
        raise ValueError(f"Malformed header line 1: {lines[0]!r}") from exc

    if rev < 31.0 or rev >= 32.0:
        raise ValueError(f"Expected PSS/E v31 (REV=31.x), got REV={rev}")

    case_id = lines[1].strip()
    case_id2 = lines[2].strip()

    return HeaderInfo(
        ic=ic,
        sbase=sbase,
        rev=rev,
        xfrrat=xfrrat,
        nxfrat=nxfrat,
        basfrq=basfrq,
        case_id=case_id,
        case_id2=case_id2,
    )


def count_section_records(line_iter: Iterator[str], section_index: int) -> int:
    """Count records in one PSS/E section.

    Handles special cases:
    - Transformer (section_index=5): 4 lines per 2-winding, 5 lines per 3-winding.
    - Multi-Terminal DC (section_index=10): Variable-length records.

    Args:
        line_iter: Iterator over remaining lines in the file.
        section_index: 0-based index of the current section.

    Returns:
        Number of records in this section.
    """
    count = 0

    if section_index == 5:
        # Transformer section: multi-line records
        for line in line_iter:
            if _is_sentinel(line):
                break
            # This is line 1 of a transformer record
            # Determine 2W vs 3W by checking K (3rd bus number, field index 2)
            parts = line.split(",")
            try:
                k = int(parts[2].strip())
            except (ValueError, IndexError):
                k = 0
            # Line 1 already consumed. Read lines 2, 3, 4.
            next(line_iter)  # line 2
            next(line_iter)  # line 3
            next(line_iter)  # line 4
            if k != 0:
                next(line_iter)  # line 5 for 3-winding
            count += 1

    elif section_index == 10:
        # Multi-Terminal DC section: variable-length records
        for line in line_iter:
            if _is_sentinel(line):
                break
            # First line has NCONV, NDCBS, NDCLN, ...
            parts = line.split(",")
            try:
                nconv = int(parts[0].strip())
                ndcbs = int(parts[1].strip())
                ndcln = int(parts[2].strip())
            except (ValueError, IndexError):
                nconv = ndcbs = ndcln = 0
            # Read nconv converter lines, ndcbs DC bus lines, ndcln DC link lines
            for _ in range(nconv):
                next(line_iter)
            for _ in range(ndcbs):
                next(line_iter)
            for _ in range(ndcln):
                next(line_iter)
            count += 1

    else:
        # Standard single-line-per-record section
        for line in line_iter:
            if _is_sentinel(line):
                break
            count += 1

    return count


def count_raw_records(raw_path: str | Path) -> RecordCountSummary:
    """Read a PSS/E v31 RAW file and count all records. Streaming single-pass.

    Args:
        raw_path: Path to the RAW file.

    Returns:
        RecordCountSummary with counts for all 17 sections.

    Raises:
        ValueError: If the header is malformed or not v31.
        FileNotFoundError: If the file does not exist.
    """
    raw_path = Path(raw_path)
    if not raw_path.exists():
        raise FileNotFoundError(f"RAW file not found: {raw_path}")

    with open(raw_path, encoding="utf-8", errors="replace") as f:
        all_lines = f.readlines()

    # Parse 3-line header
    header = parse_header(all_lines[:3])

    # Count records in each of 17 sections
    line_iter = iter(all_lines[3:])
    section_counts: dict[str, int] = {}

    for idx, section_name in enumerate(PSSE_V31_SECTION_NAMES):
        section_counts[section_name] = count_section_records(line_iter, idx)

    total_data_lines = sum(section_counts.values())
    non_empty_sections = [name for name, cnt in section_counts.items() if cnt > 0]
    hvdc_facts_present = {key: section_counts.get(key, 0) > 0 for key in _HVDC_FACTS_KEYS}

    return RecordCountSummary(
        header=header,
        section_counts=section_counts,
        total_data_lines=total_data_lines,
        non_empty_sections=non_empty_sections,
        total_sections=len(PSSE_V31_SECTION_NAMES),
        hvdc_facts_present=hvdc_facts_present,
    )


def summary_to_dict(summary: RecordCountSummary) -> dict:
    """Convert a RecordCountSummary to a JSON-serializable dict.

    Args:
        summary: The summary to convert.

    Returns:
        A dict suitable for ``json.dumps()``.
    """
    return {
        "header": {
            "ic": summary.header.ic,
            "sbase": summary.header.sbase,
            "rev": summary.header.rev,
            "xfrrat": summary.header.xfrrat,
            "nxfrat": summary.header.nxfrat,
            "basfrq": summary.header.basfrq,
            "case_id": summary.header.case_id,
            "case_id2": summary.header.case_id2,
        },
        "section_counts": summary.section_counts,
        "total_data_lines": summary.total_data_lines,
        "non_empty_sections": summary.non_empty_sections,
        "total_sections": summary.total_sections,
        "hvdc_facts_present": summary.hvdc_facts_present,
    }


def main(argv: list[str] | None = None) -> None:
    """CLI entry point: python -m raw_record_counter /path/to/file.raw [-o output.json]"""
    parser = argparse.ArgumentParser(
        description="Count records per section in a PSS/E v31 RAW file."
    )
    parser.add_argument("raw_file", type=str, help="Path to the PSS/E v31 RAW file")
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="Output JSON file path (default: print to stdout)",
    )
    args = parser.parse_args(argv)

    summary = count_raw_records(args.raw_file)
    result = summary_to_dict(summary)
    output_text = json.dumps(result, indent=2) + "\n"

    if args.output:
        Path(args.output).write_text(output_text, encoding="utf-8")
        print(f"Results written to {args.output}", file=sys.stderr)
    else:
        print(output_text)
