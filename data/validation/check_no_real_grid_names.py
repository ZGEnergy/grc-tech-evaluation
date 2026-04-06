"""Block references to real grid and grid-operator names in committed files."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


def _phrase(*parts: str) -> str:
    """Build a forbidden phrase without spelling it literally in source."""
    return " ".join(parts)


def _token(*parts: str) -> str:
    """Build a forbidden token without spelling it literally in source."""
    return "".join(parts)


# Keep the list explicit to avoid accidental regex false positives.
FORBIDDEN_TERMS: tuple[str, ...] = (
    _phrase("California", "Independent", "System", "Operator"),
    _phrase("Electric", "Reliability", "Council", "of", "Texas"),
    _phrase("Western", "Electricity", "Coordinating", "Council"),
    _phrase("Northeast", "Power", "Coordinating", "Council"),
    _phrase("Midwest", "Reliability", "Organization"),
    _phrase("Florida", "Reliability", "Coordinating", "Council"),
    _phrase("Texas", "Reliability", "Entity"),
    _phrase(_token("SE", "RC"), "Reliability", "Corporation"),
    _phrase("New", "York", "Independent", "System", "Operator"),
    _phrase("Midcontinent", "Independent", "System", "Operator"),
    _phrase("Southwest", "Power", "Pool"),
    _phrase(_token("P", "J", "M"), "Interconnection"),
    _phrase("ISO", "New", "England"),
    _phrase("Independent", "Electricity", "System", "Operator"),
    _phrase("Alberta", "Electric", "System", "Operator"),
    _phrase("Australian", "Energy", "Market", "Operator"),
    _phrase("National", "Energy", "System", "Operator"),
    _phrase("National", "Grid", "ESO"),
    _phrase("Eastern", "Interconnection"),
    _phrase("Western", "Interconnection"),
    _phrase("Texas", "Interconnection"),
    _token("Reliability", "First"),
    _token("CA", "ISO"),
    _token("ER", "COT"),
    _token("P", "J", "M"),
    _token("MI", "SO"),
    _token("NY", "ISO"),
    _token("ISO", "-", "NE"),
    _token("ISO", "NE"),
    _token("S", "P", "P"),
    _token("WE", "CC"),
    _token("NP", "CC"),
    _token("SE", "RC"),
    _token("R", "F", "C"),
    _token("T", "R", "E"),
    _token("M", "R", "O"),
    _token("FR", "CC"),
    _token("NE", "RC"),
    _token("IE", "SO"),
    _token("AE", "SO"),
    _token("AE", "MO"),
    _token("NE", "SO"),
)

_TERM_PATTERN = re.compile(
    "|".join(rf"\b{re.escape(term)}\b" for term in sorted(FORBIDDEN_TERMS, key=len, reverse=True)),
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class Violation:
    """One forbidden term found in one file line."""

    path: Path
    line_number: int
    term: str
    line: str


def _is_binary(path: Path) -> bool:
    """Return True when the file appears to be binary."""
    try:
        chunk = path.read_bytes()[:4096]
    except OSError:
        return False
    return b"\x00" in chunk


def scan_file(path: Path) -> list[Violation]:
    """Scan one file and return any forbidden-name violations."""
    if not path.is_file() or _is_binary(path):
        return []

    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8", errors="replace")

    violations: list[Violation] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for match in _TERM_PATTERN.finditer(line):
            violations.append(
                Violation(
                    path=path,
                    line_number=line_number,
                    term=match.group(0),
                    line=line.strip(),
                )
            )
    return violations


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""
    parser = argparse.ArgumentParser(
        description=("Fail when staged files reference real grids or grid-operating entities.")
    )
    parser.add_argument("paths", nargs="*", help="Files to scan.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the scanner on the provided file paths."""
    args = build_parser().parse_args(argv)
    paths = [Path(path) for path in args.paths]

    violations: list[Violation] = []
    for path in paths:
        violations.extend(scan_file(path))

    if not violations:
        return 0

    print(
        "Found forbidden real grid or grid-operator references. "
        "Use fictional or generic names instead.",
        file=sys.stderr,
    )
    for violation in violations:
        print(
            f"{violation.path}:{violation.line_number}: "
            f"matched '{violation.term}' -> {violation.line}",
            file=sys.stderr,
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
