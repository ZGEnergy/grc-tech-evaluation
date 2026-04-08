"""MATPOWER psse2mpc parser wrapper.

Orchestrates Octave/MATPOWER's ``psse2mpc`` function to convert a PSS/E RAW file
into MATPOWER case struct CSV exports, then inspects the results and records
parser warnings, known limitations, and field-level record counts.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from fnm.scripts.fnm_gating import find_repo_root

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MPC_FIELD_COLUMNS: dict[str, int] = {
    "bus": 13,
    "gen": 21,
    "branch": 13,
    "gencost": 7,  # minimum; variable-width cost models may have more
    "areas": 2,
    "dcline": 17,
    "bus_name": 1,
}

MPC_DROPPED_RECORD_TYPES: tuple[str, ...] = (
    "Two-Terminal DC",
    "VSC DC",
    "Multi-Terminal DC",
    "Multi-Section Line",
    "Impedance Correction",
    "FACTS",
)

MPC_LOSSY_RECORD_TYPES: tuple[str, ...] = (
    "Switched Shunt",
    "Fixed Shunt",
    "Transformer",
)

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

SectionCountMap = dict[str, int]

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ParserWarning:
    """A single warning emitted by psse2mpc during conversion.

    Attributes:
        line: Raw warning text from stderr.
        category: Classification of the warning (e.g. ``skipped_record``,
            ``phantom_bus``, ``unsupported_field``, ``conversion_warning``).
    """

    line: str
    category: str


@dataclass(frozen=True)
class KnownLimitation:
    """A known limitation of MATPOWER's PSS/E parser.

    Attributes:
        record_type: PSS/E section name (e.g. ``"Two-Terminal DC"``).
        behavior: Whether this record type is ``"dropped"`` or ``"lossy"``.
        description: Human-readable explanation.
    """

    record_type: str
    behavior: str
    description: str


@dataclass
class MatpowerParserLog:
    """Full log from a single psse2mpc invocation.

    Attributes:
        raw_path: Path to the input PSS/E RAW file.
        output_dir: Directory where CSV exports were written.
        return_code: Octave process exit code.
        stdout: Raw stdout from the Octave process.
        stderr: Raw stderr from the Octave process.
        baseMVA: Parsed base MVA value, or None.
        version: Parsed MATPOWER case version string, or None.
        field_counts_octave: Record counts reported by Octave stdout.
        field_counts_csv: Record counts measured from written CSV files.
        warnings: Classified parser warnings.
    """

    raw_path: str
    output_dir: str
    return_code: int
    stdout: str
    stderr: str
    baseMVA: float | None = None
    version: str | None = None
    field_counts_octave: SectionCountMap = field(default_factory=dict)
    field_counts_csv: SectionCountMap = field(default_factory=dict)
    warnings: list[ParserWarning] = field(default_factory=list)


@dataclass
class MatpowerParserSummary:
    """High-level summary combining parser log with known limitations.

    Attributes:
        log: The underlying parser log.
        known_limitations: List of known MATPOWER parser limitations.
        success: Whether the conversion completed without error.
    """

    log: MatpowerParserLog
    known_limitations: list[KnownLimitation]
    success: bool


# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------


def find_matpower_path() -> Path | None:
    """Search for the MATPOWER installation directory.

    Checks (in order):
      1. ``MATPOWER_PATH`` environment variable.
      2. ``evaluations/matpower/matpower8.1`` relative to repo root.
      3. ``/workspace/evaluations/matpower/matpower8.1`` (container default).

    Returns:
        Path to the MATPOWER installation, or None if not found.
    """
    import os

    # 1. Environment variable
    env_path = os.environ.get("MATPOWER_PATH")
    if env_path:
        p = Path(env_path)
        if p.is_dir():
            return p

    # 2. Relative to repo root
    try:
        repo_root = find_repo_root()
        candidate = repo_root / "evaluations" / "matpower" / "matpower8.1"
        if candidate.is_dir():
            return candidate
    except FileNotFoundError:
        pass

    # 3. Check if we're in a worktree — look for the main checkout
    try:
        repo_root = find_repo_root()
        # If in a worktree, check the git main working tree
        git_dir = repo_root / ".git"
        if git_dir.is_file():
            # .git is a file in worktrees, pointing to the main .git dir
            text = git_dir.read_text().strip()
            if text.startswith("gitdir:"):
                main_git = Path(text.split(":", 1)[1].strip())
                # main_git is like <main_repo>/.git/worktrees/<name>
                main_repo = main_git.parent.parent.parent
                candidate = main_repo / "evaluations" / "matpower" / "matpower8.1"
                if candidate.is_dir():
                    return candidate
    except (FileNotFoundError, OSError):
        pass

    # 4. Container default
    container_default = Path("/workspace/evaluations/matpower/matpower8.1")
    if container_default.is_dir():
        return container_default

    return None


def build_octave_command(
    raw_path: str | Path,
    output_dir: str | Path,
    matpower_path: str | Path | None = None,
) -> list[str]:
    """Build the command list for invoking the Octave psse2mpc script.

    Args:
        raw_path: Path to the PSS/E RAW file.
        output_dir: Directory for CSV output.
        matpower_path: Optional path to MATPOWER installation. If None,
            the Octave script will use its built-in default.

    Returns:
        A list of strings suitable for ``subprocess.run()``.
    """
    repo_root = find_repo_root()
    script_path = str(repo_root / "data" / "fnm" / "scripts" / "run_psse2mpc.m")
    cmd = [
        "octave",
        "--no-gui",
        "--no-init-file",
        script_path,
        str(raw_path),
        str(output_dir),
    ]
    if matpower_path is not None:
        cmd.append(str(matpower_path))
    return cmd


def run_psse2mpc(
    raw_path: str | Path,
    output_dir: str | Path,
    matpower_path: str | Path | None = None,
    *,
    timeout: int = 300,
) -> MatpowerParserLog:
    """Run psse2mpc via Octave and return a structured parser log.

    Args:
        raw_path: Path to the PSS/E RAW file.
        output_dir: Directory for CSV output.
        matpower_path: Optional path to MATPOWER installation.
        timeout: Maximum seconds to wait for Octave (default 300).

    Returns:
        A MatpowerParserLog with all parsed results.
    """
    raw_path = Path(raw_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Auto-detect MATPOWER path if not provided
    if matpower_path is None:
        matpower_path = find_matpower_path()

    cmd = build_octave_command(raw_path, output_dir, matpower_path)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return MatpowerParserLog(
            raw_path=str(raw_path),
            output_dir=str(output_dir),
            return_code=-1,
            stdout="",
            stderr="Octave process timed out",
        )

    log = MatpowerParserLog(
        raw_path=str(raw_path),
        output_dir=str(output_dir),
        return_code=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
    )

    # Parse stdout for structured data
    parsed = parse_octave_stdout(result.stdout)
    if "_baseMVA" in parsed:
        log.baseMVA = parsed["_baseMVA"]
    if "_version" in parsed:
        log.version = parsed["_version"]
    log.field_counts_octave = {k: v for k, v in parsed.items() if not k.startswith("_")}

    # Parse stderr for warnings
    log.warnings = parse_octave_warnings(result.stderr)

    # Read CSV file counts
    log.field_counts_csv = read_csv_field_counts(output_dir)

    return log


def parse_octave_stdout(stdout: str) -> dict:
    """Parse structured output lines from the Octave script.

    Recognizes:
      - ``MPC_BASEMVA:<float>`` -> ``{"_baseMVA": <float>}``
      - ``MPC_VERSION:<string>`` -> ``{"_version": <string>}``
      - ``MPC_FIELD_COUNT:<name>:<int>`` -> ``{<name>: <int>}``

    Args:
        stdout: Raw stdout string from Octave.

    Returns:
        Dict with parsed values. Special keys prefixed with ``_``.
    """
    result: dict = {}
    if not stdout or not stdout.strip():
        return result

    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith("MPC_BASEMVA:"):
            try:
                result["_baseMVA"] = float(line.split(":", 1)[1])
            except (ValueError, IndexError):
                pass
        elif line.startswith("MPC_VERSION:"):
            try:
                result["_version"] = line.split(":", 1)[1].strip()
            except IndexError:
                pass
        elif line.startswith("MPC_FIELD_COUNT:"):
            parts = line.split(":")
            if len(parts) >= 3:
                field_name = parts[1]
                try:
                    count = int(parts[2])
                    result[field_name] = count
                except ValueError:
                    pass

    return result


def parse_octave_warnings(stderr: str) -> list[ParserWarning]:
    """Classify Octave stderr lines into warning categories.

    Categories:
      - ``skipped_record``: Record type was skipped/ignored during conversion.
      - ``phantom_bus``: Bus referenced but not defined in the bus table.
      - ``unsupported_field``: Field or data type not supported by the parser.
      - ``conversion_warning``: Generic conversion warning.

    Args:
        stderr: Raw stderr string from Octave.

    Returns:
        List of classified ParserWarning objects.
    """
    warnings: list[ParserWarning] = []
    if not stderr:
        return warnings

    for line in stderr.splitlines():
        line = line.strip()
        if not line:
            continue

        category = _classify_warning(line)
        warnings.append(ParserWarning(line=line, category=category))

    return warnings


def _classify_warning(line: str) -> str:
    """Classify a single warning line by keyword matching."""
    lower = line.lower()
    if any(kw in lower for kw in ("skip", "ignor", "discard", "dropped")):
        return "skipped_record"
    if any(kw in lower for kw in ("phantom", "missing bus", "undefined bus")):
        return "phantom_bus"
    if any(kw in lower for kw in ("unsupported", "unrecognized", "unknown field")):
        return "unsupported_field"
    return "conversion_warning"


def read_csv_field_counts(output_dir: str | Path) -> SectionCountMap:
    """Count rows in each ``mpc_*.csv`` file in the output directory.

    Rows are counted by number of non-empty lines. ``csvwrite`` from Octave
    does not produce a header row, so all lines are data lines.

    Args:
        output_dir: Directory containing the CSV exports.

    Returns:
        Dict mapping field name (e.g. ``"bus"``) to row count.
    """
    output_dir = Path(output_dir)
    counts: SectionCountMap = {}

    for csv_path in sorted(output_dir.glob("mpc_*.csv")):
        # Extract field name: mpc_bus.csv -> bus
        match = re.match(r"mpc_(.+)\.csv$", csv_path.name)
        if not match:
            continue
        field_name = match.group(1)
        try:
            text = csv_path.read_text(encoding="utf-8")
            row_count = sum(1 for line in text.splitlines() if line.strip())
            counts[field_name] = row_count
        except OSError:
            counts[field_name] = 0

    return counts


def build_known_limitations() -> list[KnownLimitation]:
    """Build the list of known MATPOWER parser limitations.

    Covers all record types in ``MPC_DROPPED_RECORD_TYPES`` and
    ``MPC_LOSSY_RECORD_TYPES``.

    Returns:
        List of KnownLimitation objects.
    """
    limitations: list[KnownLimitation] = []

    dropped_descriptions: dict[str, str] = {
        "Two-Terminal DC": (
            "Two-terminal DC line records are not converted to MATPOWER format. "
            "The dcline field is populated from a different source or left empty."
        ),
        "VSC DC": (
            "VSC-based HVDC records are not supported by psse2mpc and are silently dropped."
        ),
        "Multi-Terminal DC": (
            "Multi-terminal DC network records are not converted. "
            "MATPOWER has no equivalent data structure."
        ),
        "Multi-Section Line": (
            "Multi-section line grouping records are dropped. "
            "Individual sections remain as separate branches."
        ),
        "Impedance Correction": (
            "Impedance correction table records are not used in the conversion. "
            "Transformer impedance is taken at nominal tap only."
        ),
        "FACTS": (
            "FACTS device records (SVC, STATCOM, TCSC) are not converted to MATPOWER format."
        ),
    }

    for rt in MPC_DROPPED_RECORD_TYPES:
        limitations.append(
            KnownLimitation(
                record_type=rt,
                behavior="dropped",
                description=dropped_descriptions.get(rt, f"{rt} records are dropped."),
            )
        )

    lossy_descriptions: dict[str, str] = {
        "Switched Shunt": (
            "Switched shunt devices are converted to fixed shunts at their initial operating "
            "point. Discrete switching steps and voltage control logic are lost."
        ),
        "Fixed Shunt": (
            "Fixed shunt admittance values are converted but may lose per-unit base "
            "information if the bus voltage base differs from system base."
        ),
        "Transformer": (
            "Transformer records are converted but impedance correction tables, "
            "phase-shifting angle limits, and multi-winding control modes may be "
            "simplified or lost."
        ),
    }

    for rt in MPC_LOSSY_RECORD_TYPES:
        limitations.append(
            KnownLimitation(
                record_type=rt,
                behavior="lossy",
                description=lossy_descriptions.get(rt, f"{rt} conversion is lossy."),
            )
        )

    return limitations


def log_to_dict(log: MatpowerParserLog) -> dict:
    """Convert a MatpowerParserLog to a JSON-serializable dict.

    Args:
        log: The parser log to convert.

    Returns:
        A dict suitable for ``json.dumps()``.
    """
    return {
        "raw_path": log.raw_path,
        "output_dir": log.output_dir,
        "return_code": log.return_code,
        "baseMVA": log.baseMVA,
        "version": log.version,
        "field_counts_octave": log.field_counts_octave,
        "field_counts_csv": log.field_counts_csv,
        "warnings": [{"line": w.line, "category": w.category} for w in log.warnings],
        "stdout_length": len(log.stdout),
        "stderr_length": len(log.stderr),
    }


def summary_to_dict(summary: MatpowerParserSummary) -> dict:
    """Convert a MatpowerParserSummary to a JSON-serializable dict.

    Args:
        summary: The parser summary to convert.

    Returns:
        A dict suitable for ``json.dumps()``.
    """
    return {
        "success": summary.success,
        "log": log_to_dict(summary.log),
        "known_limitations": [
            {
                "record_type": kl.record_type,
                "behavior": kl.behavior,
                "description": kl.description,
            }
            for kl in summary.known_limitations
        ],
    }


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for MATPOWER parser execution.

    Usage::

        python -m fnm.scripts.matpower_parser <raw_path> <output_dir> [--matpower-path PATH]
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Run MATPOWER psse2mpc on a PSS/E RAW file and export results."
    )
    parser.add_argument("raw_path", type=str, help="Path to the PSS/E RAW file")
    parser.add_argument("output_dir", type=str, help="Directory for CSV exports")
    parser.add_argument(
        "--matpower-path",
        type=str,
        default=None,
        help="Path to MATPOWER installation directory",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="Output JSON file path (default: print to stdout)",
    )
    args = parser.parse_args(argv)

    log = run_psse2mpc(args.raw_path, args.output_dir, args.matpower_path)
    limitations = build_known_limitations()
    summary = MatpowerParserSummary(
        log=log,
        known_limitations=limitations,
        success=log.return_code == 0,
    )

    result = summary_to_dict(summary)
    output_text = json.dumps(result, indent=2) + "\n"

    if args.output:
        Path(args.output).write_text(output_text, encoding="utf-8")
        print(f"Results written to {args.output}", file=sys.stderr)
    else:
        print(output_text)
