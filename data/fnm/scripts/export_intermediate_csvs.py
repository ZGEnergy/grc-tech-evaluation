"""Export Pipeline Script -- MATPOWER .mat to intermediate-format CSVs.

Reads the cleaned MATPOWER case file, extracts all 17 PSS/E v31 record types
into separate intermediate-format CSV files, writes a sidecar manifest.json,
and validates every output artifact against existing JSON Schema files.

Key transformations:
  - Splits MATPOWER branch matrix into separate branch.csv and transformer.csv
  - Converts MATPOWER tap=0 sentinel to PSS/E-standard 1.0
  - Filters to main-island buses using the excluded bus registry
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import jsonschema

from fnm.scripts.intermediate_schema import (
    FieldSpec,
    TableSchema,
    get_table_schemas,
)
from fnm.scripts.raw_record_counter import PSSE_V31_SECTION_NAMES

# ---------------------------------------------------------------------------
# MATPOWER column definitions (0-indexed)
# ---------------------------------------------------------------------------

# bus columns: bus_i(0), type(1), Pd(2), Qd(3), Gs(4), Bs(5), area(6),
#              Vm(7), Va(8), baseKV(9), zone(10), Vmax(11), Vmin(12)
_BUS_COLS = 13

# gen columns: bus(0), Pg(1), Qg(2), Qmax(3), Qmin(4), Vg(5), mBase(6),
#              status(7), Pmax(8), Pmin(9), ...21 total
_GEN_COLS = 21

# branch columns: fbus(0), tbus(1), r(2), x(3), b(4), rateA(5), rateB(6),
#                  rateC(7), tap(8), shift(9), status(10), angmin(11), angmax(12)
_BRANCH_COLS = 13

# gencost: model(0), startup(1), shutdown(2), ncost(3), cost_coeffs(4+)

# MATPOWER branch column indices for transformer detection
_TAP_COL = 8
_SHIFT_COL = 9


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MatpowerCase:
    """Parsed contents of a MATPOWER .mat case file."""

    baseMVA: float
    version: str
    bus: list[list[float]]
    gen: list[list[float]]
    branch: list[list[float]]
    gencost: list[list[float]]
    areas: list[list[float]]
    bus_name: list[str]
    dcline: list[list[float]]


@dataclass(frozen=True)
class TableExport:
    """Metadata about one exported CSV table."""

    table_name: str
    record_type: str
    file_name: str
    file_path: Path
    record_count: int
    column_count: int
    schema_file: str


@dataclass(frozen=True)
class ExportManifest:
    """Top-level manifest for the intermediate CSV export."""

    sbase: float
    basfrq: float
    rev: float
    case_id: str
    canonical_parser: str
    tables: list[TableExport]
    total_records: int
    total_tables: int
    non_empty_record_types: list[str]
    schema_version: str
    generated_timestamp: str


@dataclass(frozen=True)
class ValidationResult:
    """Result of validating one CSV or manifest against its JSON Schema."""

    artifact_name: str
    is_valid: bool
    errors: list[str]
    rows_checked: int


@dataclass
class ExportResult:
    """Aggregate result of the full export pipeline."""

    manifest: ExportManifest
    table_exports: list[TableExport]
    validations: list[ValidationResult]
    output_dir: Path
    success: bool
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Table name helpers
# ---------------------------------------------------------------------------

_RECORD_TYPE_TO_TABLE: dict[str, str] = {
    rt: rt.lower().replace(" ", "_").replace("-", "_") for rt in PSSE_V31_SECTION_NAMES
}


def _table_name(record_type: str) -> str:
    return _RECORD_TYPE_TO_TABLE[record_type]


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------


def load_matpower_case(mat_path: Path) -> MatpowerCase:
    """Load a MATPOWER .mat case file into a structured container.

    Supports Octave text-format ``.mat`` files (the format produced by
    ``save -text``). Falls back to ``scipy.io.loadmat`` for MATLAB v5 binary
    files.

    Args:
        mat_path: Path to the .mat file.

    Returns:
        A MatpowerCase with all parsed matrices.

    Raises:
        FileNotFoundError: If the file does not exist.
        KeyError: If the .mat file lacks the expected ``mpc`` struct fields.
    """
    if not mat_path.exists():
        raise FileNotFoundError(f"MAT file not found: {mat_path}")

    # Detect file format by reading the first line
    with open(mat_path, encoding="utf-8", errors="replace") as f:
        first_line = f.readline()

    if first_line.startswith("# Created by Octave") or first_line.startswith("#"):
        return _load_octave_text_mat(mat_path)

    return _load_scipy_mat(mat_path)


def _load_octave_text_mat(mat_path: Path) -> MatpowerCase:
    """Parse an Octave text-format .mat file containing a MATPOWER case struct.

    The Octave text format uses ``# name:``, ``# type:``, ``# rows:``,
    ``# columns:`` directives followed by data lines.
    """
    with open(mat_path, encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    # Parse into named fields within the top-level struct
    fields: dict[str, list[list[float]] | float | str | list[str]] = {}
    i = 0
    n = len(lines)

    # Skip until we find the struct
    while i < n:
        line = lines[i].strip()
        if line.startswith("# type: scalar struct"):
            i += 1
            break
        i += 1

    # Skip ndims and length lines
    while i < n:
        line = lines[i].strip()
        if line.startswith("# length:"):
            i += 1
            break
        i += 1

    # Now parse struct fields
    while i < n:
        line = lines[i].strip()
        if not line.startswith("# name:"):
            i += 1
            continue

        field_name = line.split(":", 1)[1].strip()
        i += 1
        if i >= n:
            break

        type_line = lines[i].strip()
        if not type_line.startswith("# type:"):
            continue
        field_type = type_line.split(":", 1)[1].strip()
        i += 1

        if field_type == "scalar":
            # Read scalar value
            while i < n and (not lines[i].strip() or lines[i].startswith("#")):
                i += 1
            if i < n:
                try:
                    fields[field_name] = float(lines[i].strip())
                except ValueError:
                    fields[field_name] = lines[i].strip()
                i += 1

        elif field_type == "matrix":
            # Read rows/columns then data
            rows = 0
            while i < n:
                rl = lines[i].strip()
                if rl.startswith("# rows:"):
                    rows = int(rl.split(":", 1)[1].strip())
                elif rl.startswith("# columns:"):
                    _ = int(rl.split(":", 1)[1].strip())
                    i += 1
                    break
                i += 1

            matrix: list[list[float]] = []
            for _ in range(rows):
                if i >= n:
                    break
                data_line = lines[i].strip()
                if data_line and not data_line.startswith("#"):
                    vals = [float(v) for v in data_line.split()]
                    matrix.append(vals)
                i += 1
            fields[field_name] = matrix

        elif field_type == "sq_string":
            # Read string value
            # Skip elements/length lines
            while i < n:
                sl = lines[i].strip()
                if sl.startswith("# elements:") or sl.startswith("# length:"):
                    i += 1
                    continue
                break
            if i < n:
                fields[field_name] = lines[i].strip()
                i += 1

        elif field_type == "cell":
            # Cell array of strings
            cell_rows = 0
            while i < n:
                cl = lines[i].strip()
                if cl.startswith("# rows:"):
                    cell_rows = int(cl.split(":", 1)[1].strip())
                elif cl.startswith("# columns:"):
                    i += 1
                    break
                i += 1

            string_list: list[str] = []
            for _ in range(cell_rows):
                # Skip cell-element and type headers
                while i < n:
                    cl = lines[i].strip()
                    if cl.startswith("# name: <cell-element>"):
                        i += 1
                        continue
                    if cl.startswith("# type:"):
                        i += 1
                        continue
                    if cl.startswith("# elements:"):
                        i += 1
                        continue
                    if cl.startswith("# length:"):
                        i += 1
                        break
                    i += 1
                # Read the string value
                if i < n:
                    string_list.append(lines[i].rstrip("\n"))
                    i += 1
            fields[field_name] = string_list

        else:
            i += 1

    # Extract fields
    baseMVA = float(fields.get("baseMVA", 100.0))
    version = str(fields.get("version", "2"))

    def _get_matrix(name: str) -> list[list[float]]:
        val = fields.get(name, [])
        if isinstance(val, list):
            return val  # type: ignore[return-value]
        return []

    def _get_strings(name: str) -> list[str]:
        val = fields.get(name, [])
        if isinstance(val, list) and all(isinstance(v, str) for v in val):
            return val  # type: ignore[return-value]
        return []

    return MatpowerCase(
        baseMVA=baseMVA,
        version=version,
        bus=_get_matrix("bus"),
        gen=_get_matrix("gen"),
        branch=_get_matrix("branch"),
        gencost=_get_matrix("gencost"),
        areas=_get_matrix("areas"),
        bus_name=_get_strings("bus_name"),
        dcline=_get_matrix("dcline"),
    )


def _load_scipy_mat(mat_path: Path) -> MatpowerCase:
    """Load a MATLAB v5 binary .mat file using scipy."""
    import scipy.io

    mat = scipy.io.loadmat(str(mat_path), squeeze_me=False)

    mpc = None
    for key in mat:
        if key.startswith("_"):
            continue
        val = mat[key]
        if hasattr(val, "dtype") and val.dtype.names is not None:
            mpc = val
            break

    if mpc is None:
        raise KeyError("No MATPOWER case struct found in .mat file")

    def _extract_scalar(name: str, default: float | str = 0.0) -> float | str:
        try:
            v = mpc[name][0, 0]
            if hasattr(v, "flat"):
                return float(v.flat[0])
            return v
        except (KeyError, IndexError, ValueError):
            return default

    def _extract_matrix(name: str) -> list[list[float]]:
        try:
            arr = mpc[name][0, 0]
            return arr.tolist()
        except (KeyError, IndexError):
            return []

    def _extract_strings(name: str) -> list[str]:
        try:
            arr = mpc[name][0, 0]
            result: list[str] = []
            for row in arr:
                if hasattr(row, "__len__") and not isinstance(row, str):
                    if len(row) > 0 and hasattr(row[0], "__len__"):
                        result.append(str(row[0]).strip())
                    else:
                        result.append(str(row).strip())
                else:
                    result.append(str(row).strip())
            return result
        except (KeyError, IndexError):
            return []

    baseMVA = float(_extract_scalar("baseMVA", 100.0))
    version = str(_extract_scalar("version", "2"))

    return MatpowerCase(
        baseMVA=baseMVA,
        version=version,
        bus=_extract_matrix("bus"),
        gen=_extract_matrix("gen"),
        branch=_extract_matrix("branch"),
        gencost=_extract_matrix("gencost"),
        areas=_extract_matrix("areas"),
        bus_name=_extract_strings("bus_name"),
        dcline=_extract_matrix("dcline"),
    )


def load_excluded_buses(excluded_buses_path: Path) -> set[int]:
    """Load the set of excluded bus numbers from the JSON registry.

    Supports both formats:
      - Full registry JSON with top-level ``excluded_buses`` array of objects
        (each with a ``bus_number`` field)
      - Simple JSON array of integers

    Args:
        excluded_buses_path: Path to the excluded buses JSON file.

    Returns:
        Set of integer bus numbers to exclude.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    if not excluded_buses_path.exists():
        raise FileNotFoundError(f"Excluded buses file not found: {excluded_buses_path}")

    data = json.loads(excluded_buses_path.read_text(encoding="utf-8"))

    if isinstance(data, list):
        return {int(b) for b in data}

    # Full registry format
    buses = data.get("excluded_buses", [])
    return {int(b["bus_number"]) for b in buses}


def normalize_tap_ratio(tap: float) -> float:
    """Convert MATPOWER tap=0 sentinel to PSS/E-standard 1.0.

    In MATPOWER, a tap ratio of 0.0 means "nominal turns ratio" (i.e. 1.0).
    PSS/E uses an explicit 1.0 value instead. This function performs that
    conversion.

    Args:
        tap: The tap ratio value from MATPOWER.

    Returns:
        1.0 if tap == 0.0, otherwise the original value.
    """
    return 1.0 if tap == 0.0 else tap


def split_branches_and_transformers(
    branch_matrix: list[list[float]],
    bus_numbers: set[int],
) -> tuple[list[dict[str, int | float | str]], list[dict[str, int | float | str]]]:
    """Split the MATPOWER branch matrix into branch and transformer rows.

    A row is classified as a transformer if tap ratio (col 8) != 0 or
    phase shift (col 9) != 0. Plain branches have both at 0.

    Args:
        branch_matrix: The MATPOWER branch matrix (list of rows).
        bus_numbers: Set of main-island bus numbers for filtering.

    Returns:
        Tuple of (branch_rows, transformer_rows) where each row is a dict
        with PSS/E field names as keys.
    """
    branch_schema = _get_schema_by_record_type("Branch")
    transformer_schema = _get_schema_by_record_type("Transformer")

    branch_fields = branch_schema.fields
    transformer_fields = transformer_schema.fields

    branches: list[dict[str, int | float | str]] = []
    transformers: list[dict[str, int | float | str]] = []

    for row in branch_matrix:
        fbus = int(row[0])
        tbus = int(row[1])

        # Filter: both endpoints must be in bus_numbers
        if fbus not in bus_numbers or tbus not in bus_numbers:
            continue

        tap = row[_TAP_COL] if len(row) > _TAP_COL else 0.0
        shift = row[_SHIFT_COL] if len(row) > _SHIFT_COL else 0.0

        is_transformer = (tap != 0.0) or (shift != 0.0)

        if is_transformer:
            xfmr_row = _matpower_branch_to_transformer(row, transformer_fields)
            transformers.append(xfmr_row)
        else:
            br_row = _matpower_branch_to_branch(row, branch_fields)
            branches.append(br_row)

    return branches, transformers


def _matpower_branch_to_branch(
    row: list[float],
    fields: list[FieldSpec],
) -> dict[str, int | float | str]:
    """Convert a MATPOWER branch row to a PSS/E branch dict."""
    # MATPOWER branch: fbus(0), tbus(1), r(2), x(3), b(4), rateA(5),
    #   rateB(6), rateC(7), tap(8), shift(9), status(10), angmin(11), angmax(12)
    d: dict[str, int | float | str] = {}

    mapping = {
        "I": (0, "integer"),
        "J": (1, "integer"),
        "CKT": (None, "string"),  # default
        "R": (2, "number"),
        "X": (3, "number"),
        "B": (4, "number"),
        "RATEA": (5, "number"),
        "RATEB": (6, "number"),
        "RATEC": (7, "number"),
        "GI": (None, "number"),
        "BI": (None, "number"),
        "GJ": (None, "number"),
        "BJ": (None, "number"),
        "ST": (10, "integer"),
        "MET": (None, "integer"),
        "LEN": (None, "number"),
        "O1": (None, "integer"),
        "F1": (None, "number"),
        "O2": (None, "integer"),
        "F2": (None, "number"),
        "O3": (None, "integer"),
        "F3": (None, "number"),
        "O4": (None, "integer"),
        "F4": (None, "number"),
    }

    for f in fields:
        if f.name in mapping:
            col_idx, dtype = mapping[f.name]
            if col_idx is not None and col_idx < len(row):
                val = row[col_idx]
                d[f.name] = _cast_value(val, dtype)
            else:
                d[f.name] = _default_for_field(f)
        else:
            d[f.name] = _default_for_field(f)

    return d


def _matpower_branch_to_transformer(
    row: list[float],
    fields: list[FieldSpec],
) -> dict[str, int | float | str]:
    """Convert a MATPOWER branch row (transformer) to PSS/E transformer dict."""
    d: dict[str, int | float | str] = {}

    # Map MATPOWER branch columns to PSS/E transformer fields
    for f in fields:
        d[f.name] = _default_for_field(f)

    # Line 1 -- common identifiers
    d["I"] = int(row[0])
    d["J"] = int(row[1])
    d["K"] = 0  # 2-winding
    d["CKT"] = "1 "
    d["CW"] = 1
    d["CZ"] = 1
    d["CM"] = 1
    d["STAT"] = int(row[10]) if len(row) > 10 else 1

    # Line 2 -- impedance
    d["R1_2"] = row[2]
    d["X1_2"] = row[3]
    d["SBASE1_2"] = 100.0

    # Line 3 -- winding 1
    tap = row[_TAP_COL] if len(row) > _TAP_COL else 0.0
    d["WINDV1"] = normalize_tap_ratio(tap)
    shift = row[_SHIFT_COL] if len(row) > _SHIFT_COL else 0.0
    d["ANG1"] = shift

    # Ratings
    d["RATA1"] = row[5] if len(row) > 5 else 0.0
    d["RATB1"] = row[6] if len(row) > 6 else 0.0
    d["RATC1"] = row[7] if len(row) > 7 else 0.0

    # Winding 2 (MATPOWER doesn't store winding-2 tap -- uses 1.0 default)
    d["WINDV2"] = 1.0

    return d


def _get_schema_by_record_type(record_type: str) -> TableSchema:
    """Look up a TableSchema by PSS/E record type name."""
    for ts in get_table_schemas():
        if ts.record_type == record_type:
            return ts
    msg = f"Unknown record type: {record_type}"
    raise ValueError(msg)


def _default_for_field(f: FieldSpec) -> int | float | str:
    """Return the default value for a field spec."""
    if f.default_value is not None:
        if f.data_type == "integer":
            return int(f.default_value)
        if f.data_type == "number":
            return float(f.default_value)
        return str(f.default_value)
    # Required fields with no default -- use type-appropriate zero
    if f.data_type == "integer":
        return 0
    if f.data_type == "number":
        return 0.0
    return ""


def _cast_value(val: float, dtype: str) -> int | float | str:
    """Cast a numeric value to the specified type."""
    if dtype == "integer":
        return int(val)
    if dtype == "number":
        return float(val)
    return str(val)


def filter_rows_by_bus(
    rows: list[dict[str, int | float | str]],
    bus_numbers: set[int],
    bus_key: str = "I",
) -> list[dict[str, int | float | str]]:
    """Filter table rows to retain only those referencing main-island buses.

    Args:
        rows: List of row dicts.
        bus_numbers: Set of valid (main-island) bus numbers.
        bus_key: Column name containing the bus number to check.

    Returns:
        Filtered list of rows where the bus_key value is in bus_numbers.
    """
    return [r for r in rows if int(r[bus_key]) in bus_numbers]


def _filter_branch_rows_by_bus(
    rows: list[dict[str, int | float | str]],
    bus_numbers: set[int],
) -> list[dict[str, int | float | str]]:
    """Filter branch/transformer rows requiring both I and J in bus_numbers."""
    return [r for r in rows if int(r["I"]) in bus_numbers and int(r["J"]) in bus_numbers]


# ---------------------------------------------------------------------------
# MATPOWER -> intermediate format conversion helpers
# ---------------------------------------------------------------------------


def _matpower_bus_to_psse(
    bus_matrix: list[list[float]],
    bus_names: list[str],
    bus_numbers: set[int],
) -> list[dict[str, int | float | str]]:
    """Convert MATPOWER bus matrix rows to PSS/E bus dicts."""
    rows: list[dict[str, int | float | str]] = []

    for idx, brow in enumerate(bus_matrix):
        bus_num = int(brow[0])
        if bus_num not in bus_numbers:
            continue

        d: dict[str, int | float | str] = {}
        # I, NAME, BASKV, IDE, AREA, ZONE, OWNER, VM, VA, NVHI, NVLO, EVHI, EVLO
        d["I"] = bus_num
        d["NAME"] = bus_names[idx] if idx < len(bus_names) else "            "
        d["BASKV"] = brow[9] if len(brow) > 9 else 0.0
        d["IDE"] = int(brow[1]) if len(brow) > 1 else 1
        d["AREA"] = int(brow[6]) if len(brow) > 6 else 1
        d["ZONE"] = int(brow[10]) if len(brow) > 10 else 1
        d["OWNER"] = 1  # MATPOWER doesn't store owner per bus
        d["VM"] = brow[7] if len(brow) > 7 else 1.0
        d["VA"] = brow[8] if len(brow) > 8 else 0.0
        d["NVHI"] = brow[11] if len(brow) > 11 else 1.1
        d["NVLO"] = brow[12] if len(brow) > 12 else 0.9
        d["EVHI"] = brow[11] if len(brow) > 11 else 1.1
        d["EVLO"] = brow[12] if len(brow) > 12 else 0.9

        rows.append(d)
    return rows


def _matpower_gen_to_psse(
    gen_matrix: list[list[float]],
    bus_numbers: set[int],
) -> list[dict[str, int | float | str]]:
    """Convert MATPOWER gen matrix rows to PSS/E generator dicts."""
    rows: list[dict[str, int | float | str]] = []

    # Track per-bus generator count for ID assignment
    bus_gen_count: dict[int, int] = {}

    for grow in gen_matrix:
        bus_num = int(grow[0])
        if bus_num not in bus_numbers:
            continue

        bus_gen_count[bus_num] = bus_gen_count.get(bus_num, 0) + 1
        gen_id = str(bus_gen_count[bus_num])
        if len(gen_id) < 2:
            gen_id = gen_id + " "

        d: dict[str, int | float | str] = {}
        d["I"] = bus_num
        d["ID"] = gen_id
        d["PG"] = grow[1] if len(grow) > 1 else 0.0
        d["QG"] = grow[2] if len(grow) > 2 else 0.0
        d["QT"] = grow[3] if len(grow) > 3 else 9999.0
        d["QB"] = grow[4] if len(grow) > 4 else -9999.0
        d["VS"] = grow[5] if len(grow) > 5 else 1.0
        d["IREG"] = 0
        d["MBASE"] = grow[6] if len(grow) > 6 else 100.0
        d["ZR"] = 0.0
        d["ZX"] = 1.0
        d["RT"] = 0.0
        d["XT"] = 0.0
        d["GTAP"] = 1.0
        d["STAT"] = int(grow[7]) if len(grow) > 7 else 1
        d["RMPCT"] = 100.0
        d["PT"] = grow[8] if len(grow) > 8 else 9999.0
        d["PB"] = grow[9] if len(grow) > 9 else -9999.0
        d["O1"] = 1
        d["F1"] = 1.0
        d["O2"] = 0
        d["F2"] = 0.0
        d["O3"] = 0
        d["F3"] = 0.0
        d["O4"] = 0
        d["F4"] = 0.0
        d["WMOD"] = 0
        d["WPF"] = 1.0

        rows.append(d)
    return rows


def _matpower_bus_to_load(
    bus_matrix: list[list[float]],
    bus_numbers: set[int],
) -> list[dict[str, int | float | str]]:
    """Extract load records from MATPOWER bus matrix (Pd, Qd columns)."""
    rows: list[dict[str, int | float | str]] = []

    for brow in bus_matrix:
        bus_num = int(brow[0])
        if bus_num not in bus_numbers:
            continue

        pd = brow[2] if len(brow) > 2 else 0.0
        qd = brow[3] if len(brow) > 3 else 0.0

        # Only create load record if nonzero
        if pd == 0.0 and qd == 0.0:
            continue

        d: dict[str, int | float | str] = {}
        d["I"] = bus_num
        d["ID"] = "1 "
        d["STATUS"] = 1
        d["AREA"] = int(brow[6]) if len(brow) > 6 else 1
        d["ZONE"] = int(brow[10]) if len(brow) > 10 else 1
        d["PL"] = pd
        d["QL"] = qd
        d["IP"] = 0.0
        d["IQ"] = 0.0
        d["YP"] = 0.0
        d["YQ"] = 0.0
        d["OWNER"] = 1
        d["SCALE"] = 1

        rows.append(d)
    return rows


def _matpower_bus_to_fixed_shunt(
    bus_matrix: list[list[float]],
    bus_numbers: set[int],
) -> list[dict[str, int | float | str]]:
    """Extract fixed shunt records from MATPOWER bus matrix (Gs, Bs columns)."""
    rows: list[dict[str, int | float | str]] = []

    for brow in bus_matrix:
        bus_num = int(brow[0])
        if bus_num not in bus_numbers:
            continue

        gs = brow[4] if len(brow) > 4 else 0.0
        bs = brow[5] if len(brow) > 5 else 0.0

        if gs == 0.0 and bs == 0.0:
            continue

        d: dict[str, int | float | str] = {}
        d["I"] = bus_num
        d["ID"] = "1 "
        d["STATUS"] = 1
        d["GL"] = gs
        d["BL"] = bs

        rows.append(d)
    return rows


def _matpower_areas_to_psse(
    areas_matrix: list[list[float]],
) -> list[dict[str, int | float | str]]:
    """Convert MATPOWER areas matrix to PSS/E area dicts."""
    rows: list[dict[str, int | float | str]] = []
    for arow in areas_matrix:
        if len(arow) < 2:
            continue
        d: dict[str, int | float | str] = {}
        d["I"] = int(arow[0])
        d["ISW"] = 0
        d["PDES"] = arow[1] if len(arow) > 1 else 0.0
        d["PTOL"] = 10.0
        d["ARNAME"] = "            "
        rows.append(d)
    return rows


def _extract_zones(
    bus_matrix: list[list[float]],
    bus_numbers: set[int],
) -> list[dict[str, int | float | str]]:
    """Extract unique zones from bus data."""
    zones: set[int] = set()
    for brow in bus_matrix:
        bus_num = int(brow[0])
        if bus_num not in bus_numbers:
            continue
        zone = int(brow[10]) if len(brow) > 10 else 1
        zones.add(zone)

    return [{"I": z, "ZONAME": "            "} for z in sorted(zones)]


def _extract_owners(
    bus_numbers: set[int],
) -> list[dict[str, int | float | str]]:
    """Create a minimal owner record. MATPOWER doesn't store owner data."""
    return [{"I": 1, "OWNAME": "            "}]


def _extract_switched_shunts(
    bus_matrix: list[list[float]],
    bus_numbers: set[int],
) -> list[dict[str, int | float | str]]:
    """MATPOWER merges switched shunts into fixed -- return empty list."""
    return []


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------


def export_table_to_csv(
    rows: list[dict[str, int | float | str]],
    schema_path: Path,
    output_path: Path,
) -> TableExport:
    """Write a list of row dicts to a CSV file with column order from the schema.

    Column order is determined by the ``properties`` key order in the JSON Schema
    file. Integer-typed fields are written without decimal suffixes.

    Args:
        rows: List of row dicts to write.
        schema_path: Path to the JSON Schema for this table.
        output_path: Path to write the CSV file.

    Returns:
        A TableExport metadata record.
    """
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    columns = list(schema["properties"].keys())
    field_types = {
        name: props.get("type", "string") for name, props in schema["properties"].items()
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            # Format values: integers without .0
            formatted: dict[str, str] = {}
            for col in columns:
                val = row.get(col, "")
                ftype = field_types.get(col, "string")
                if ftype == "integer" and val != "" and val is not None:
                    try:
                        formatted[col] = str(int(float(val)))
                    except (ValueError, TypeError):
                        formatted[col] = str(val)
                elif ftype == "number" and val != "" and val is not None:
                    formatted[col] = str(float(val))
                else:
                    formatted[col] = str(val) if val is not None else ""
            writer.writerow(formatted)

    record_type = schema.get("title", output_path.stem)
    table_name = output_path.stem

    return TableExport(
        table_name=table_name,
        record_type=record_type,
        file_name=output_path.name,
        file_path=output_path,
        record_count=len(rows),
        column_count=len(columns),
        schema_file=schema_path.name,
    )


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------


def build_manifest(
    case: MatpowerCase,
    table_exports: list[TableExport],
    schema_version: str = "1.0",
) -> ExportManifest:
    """Construct the export manifest from case metadata and table exports.

    Args:
        case: The parsed MATPOWER case.
        table_exports: List of TableExport records from CSV writing.
        schema_version: Schema version string.

    Returns:
        An ExportManifest with all fields populated.
    """
    total_records = sum(te.record_count for te in table_exports)
    non_empty = [te.record_type for te in table_exports if te.record_count > 0]

    return ExportManifest(
        sbase=case.baseMVA,
        basfrq=60.0,  # North American grids use 60 Hz
        rev=31.0,
        case_id="fnm_main_island",
        canonical_parser="matpower",
        tables=table_exports,
        total_records=total_records,
        total_tables=len(table_exports),
        non_empty_record_types=non_empty,
        schema_version=schema_version,
        generated_timestamp=datetime.now(timezone.utc).isoformat(),
    )


def write_manifest(manifest: ExportManifest, output_path: Path) -> None:
    """Serialize an ExportManifest to JSON and write to disk.

    Args:
        manifest: The manifest to serialize.
        output_path: Path to write the JSON file.
    """
    data = {
        "sbase": manifest.sbase,
        "basfrq": manifest.basfrq,
        "rev": manifest.rev,
        "case_id": manifest.case_id,
        "canonical_parser": manifest.canonical_parser,
        "tables": [
            {
                "table_name": te.table_name,
                "record_type": te.record_type,
                "file_name": te.file_name,
                "record_count": te.record_count,
                "column_count": te.column_count,
                "schema_file": te.schema_file,
            }
            for te in manifest.tables
        ],
        "total_records": manifest.total_records,
        "total_tables": manifest.total_tables,
        "non_empty_record_types": manifest.non_empty_record_types,
        "schema_version": manifest.schema_version,
        "generated_timestamp": manifest.generated_timestamp,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(data, indent=2) + "\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_csv_against_schema(
    csv_path: Path,
    schema_path: Path,
) -> ValidationResult:
    """Validate every row of a CSV file against its JSON Schema.

    Each row is converted to a dict using the CSV header, cast to the schema's
    declared types, and validated with ``jsonschema.validate()``.

    Args:
        csv_path: Path to the CSV file.
        schema_path: Path to the JSON Schema file.

    Returns:
        A ValidationResult indicating pass/fail and any error messages.
    """
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    rows_checked = 0

    if not csv_path.exists():
        return ValidationResult(
            artifact_name=csv_path.name,
            is_valid=False,
            errors=[f"CSV not found: {csv_path}"],
            rows_checked=0,
        )

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            rows_checked += 1
            typed_row = _cast_csv_row(row, schema)
            try:
                jsonschema.validate(instance=typed_row, schema=schema)
            except jsonschema.ValidationError as e:
                errors.append(f"Row {idx}: {e.message}")

    return ValidationResult(
        artifact_name=csv_path.name,
        is_valid=len(errors) == 0,
        errors=errors,
        rows_checked=rows_checked,
    )


def validate_manifest_against_schema(
    manifest_path: Path,
    schema_path: Path,
) -> ValidationResult:
    """Validate a manifest.json file against manifest.schema.json.

    Args:
        manifest_path: Path to the manifest JSON file.
        schema_path: Path to the manifest JSON Schema file.

    Returns:
        A ValidationResult indicating pass/fail and any error messages.
    """
    errors: list[str] = []

    if not manifest_path.exists():
        return ValidationResult(
            artifact_name="manifest.json",
            is_valid=False,
            errors=["Manifest not found"],
            rows_checked=0,
        )

    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    try:
        jsonschema.validate(instance=manifest_data, schema=schema)
    except jsonschema.ValidationError as e:
        errors.append(e.message)

    return ValidationResult(
        artifact_name="manifest.json",
        is_valid=len(errors) == 0,
        errors=errors,
        rows_checked=1,
    )


def _cast_csv_row(
    row: dict[str, str],
    schema: dict,
) -> dict[str, int | float | str]:
    """Cast a CSV row's string values to the types declared in the schema."""
    properties = schema.get("properties", {})
    typed: dict[str, int | float | str] = {}

    for col, val in row.items():
        if col not in properties:
            typed[col] = val
            continue
        dtype = properties[col].get("type", "string")
        if val == "" or val is None:
            # Skip empty optional values
            continue
        try:
            if dtype == "integer":
                typed[col] = int(float(val))
            elif dtype == "number":
                typed[col] = float(val)
            else:
                typed[col] = val
        except (ValueError, TypeError):
            typed[col] = val

    return typed


# ---------------------------------------------------------------------------
# Pipeline orchestration
# ---------------------------------------------------------------------------


def run_export_pipeline(
    mat_path: Path,
    excluded_buses_path: Path,
    schema_dir: Path,
    output_dir: Path,
) -> ExportResult:
    """Orchestrate the full export pipeline.

    1. Load the MATPOWER .mat case
    2. Load excluded buses
    3. Compute main-island bus set
    4. For each PSS/E v31 record type, extract data, filter, export CSV
    5. Build and write manifest
    6. Validate all artifacts

    Args:
        mat_path: Path to the cleaned .mat file.
        excluded_buses_path: Path to the excluded buses JSON.
        schema_dir: Path to the directory containing JSON Schema files.
        output_dir: Path to write CSV files and manifest.

    Returns:
        An ExportResult with all metadata and validation results.
    """
    errors: list[str] = []
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load case
    case = load_matpower_case(mat_path)

    # 2. Load excluded buses
    excluded = load_excluded_buses(excluded_buses_path)

    # 3. Compute main-island bus set
    all_bus_nums = {int(row[0]) for row in case.bus}
    main_island_buses = all_bus_nums - excluded

    # 4. Extract and export each record type
    table_exports: list[TableExport] = []

    # Map record types to extraction functions
    record_type_data = _extract_all_record_types(case, main_island_buses)

    for record_type in PSSE_V31_SECTION_NAMES:
        table_name = _table_name(record_type)
        schema_file = f"{table_name}.schema.json"
        schema_path = schema_dir / schema_file
        csv_path = output_dir / f"{table_name}.csv"

        rows = record_type_data.get(record_type, [])

        if schema_path.exists():
            te = export_table_to_csv(rows, schema_path, csv_path)
        else:
            # Write with known column order from field definitions
            te = _export_table_without_schema(rows, record_type, table_name, csv_path)

        table_exports.append(te)

    # 5. Build and write manifest
    manifest = build_manifest(case, table_exports)
    manifest_path = output_dir / "manifest.json"
    write_manifest(manifest, manifest_path)

    # 6. Validate
    validations: list[ValidationResult] = []

    for te in table_exports:
        schema_path = schema_dir / te.schema_file
        if schema_path.exists():
            vr = validate_csv_against_schema(te.file_path, schema_path)
            validations.append(vr)

    manifest_schema_path = schema_dir / "manifest.schema.json"
    if manifest_schema_path.exists():
        mv = validate_manifest_against_schema(manifest_path, manifest_schema_path)
        validations.append(mv)

    # Check for failures
    for vr in validations:
        if not vr.is_valid:
            errors.extend(f"{vr.artifact_name}: {e}" for e in vr.errors)

    return ExportResult(
        manifest=manifest,
        table_exports=table_exports,
        validations=validations,
        output_dir=output_dir,
        success=len(errors) == 0,
        errors=errors,
    )


def _extract_all_record_types(
    case: MatpowerCase,
    bus_numbers: set[int],
) -> dict[str, list[dict[str, int | float | str]]]:
    """Extract data for all 17 PSS/E v31 record types from the MATPOWER case."""
    # Split branches and transformers
    branches, transformers = split_branches_and_transformers(case.branch, bus_numbers)

    data: dict[str, list[dict[str, int | float | str]]] = {}

    data["Bus"] = _matpower_bus_to_psse(case.bus, case.bus_name, bus_numbers)
    data["Load"] = _matpower_bus_to_load(case.bus, bus_numbers)
    data["Fixed Shunt"] = _matpower_bus_to_fixed_shunt(case.bus, bus_numbers)
    data["Generator"] = _matpower_gen_to_psse(case.gen, bus_numbers)
    data["Branch"] = branches
    data["Transformer"] = transformers
    data["Area"] = _matpower_areas_to_psse(case.areas)
    data["Zone"] = _extract_zones(case.bus, bus_numbers)
    data["Owner"] = _extract_owners(bus_numbers)
    data["Switched Shunt"] = _extract_switched_shunts(case.bus, bus_numbers)

    # Record types MATPOWER drops entirely -- empty
    for rt in (
        "Two-Terminal DC",
        "VSC DC",
        "Impedance Correction",
        "Multi-Terminal DC",
        "Multi-Section Line",
        "FACTS",
        "Interarea Transfer",
    ):
        data[rt] = []

    return data


def _export_table_without_schema(
    rows: list[dict[str, int | float | str]],
    record_type: str,
    table_name: str,
    output_path: Path,
) -> TableExport:
    """Export a table using field definitions from intermediate_schema.py."""
    schema = _get_schema_by_record_type(record_type)
    columns = [f.name for f in schema.fields]
    field_types = {f.name: f.data_type for f in schema.fields}

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            formatted: dict[str, str] = {}
            for col in columns:
                val = row.get(col, "")
                ftype = field_types.get(col, "string")
                if ftype == "integer" and val != "" and val is not None:
                    try:
                        formatted[col] = str(int(float(val)))
                    except (ValueError, TypeError):
                        formatted[col] = str(val)
                elif ftype == "number" and val != "" and val is not None:
                    formatted[col] = str(float(val))
                else:
                    formatted[col] = str(val) if val is not None else ""
            writer.writerow(formatted)

    return TableExport(
        table_name=table_name,
        record_type=record_type,
        file_name=output_path.name,
        file_path=output_path,
        record_count=len(rows),
        column_count=len(columns),
        schema_file=f"{table_name}.schema.json",
    )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for the export pipeline.

    Usage::

        python -m fnm.scripts.export_intermediate_csvs \\
            --mat-path data/fnm/reference/cleaned/fnm_main_island.mat \\
            --excluded-buses data/fnm/reference/excluded_buses.json \\
            --schema-dir data/fnm/intermediate/schemas \\
            --output-dir data/fnm/intermediate/tables
    """
    parser = argparse.ArgumentParser(
        description="Export MATPOWER .mat case to intermediate-format CSVs."
    )
    parser.add_argument(
        "--mat-path",
        type=Path,
        required=True,
        help="Path to the cleaned MATPOWER .mat case file.",
    )
    parser.add_argument(
        "--excluded-buses",
        type=Path,
        required=True,
        help="Path to the excluded buses JSON file.",
    )
    parser.add_argument(
        "--schema-dir",
        type=Path,
        required=True,
        help="Path to the JSON Schema directory.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Output directory for CSV files and manifest.",
    )
    args = parser.parse_args(argv)

    result = run_export_pipeline(
        mat_path=args.mat_path,
        excluded_buses_path=args.excluded_buses,
        schema_dir=args.schema_dir,
        output_dir=args.output_dir,
    )

    if result.success:
        print("Export pipeline completed successfully.")
        print(f"Output directory: {result.output_dir}")
        print(f"Tables: {result.manifest.total_tables}")
        print(f"Records: {result.manifest.total_records}")
        print(f"Non-empty types: {len(result.manifest.non_empty_record_types)}")
    else:
        print("Export pipeline FAILED:", file=sys.stderr)
        for err in result.errors:
            print(f"  {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
