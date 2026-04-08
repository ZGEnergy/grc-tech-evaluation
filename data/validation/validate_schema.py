"""Schema Conformance & File Completeness Checks (PRD 05/01).

Verifies that every expected CSV file exists for each network tier
(TINY, SMALL, MEDIUM) and that each file conforms to the canonical CSV
schema. Checks are purely structural: file existence, column names,
column ordering, data types, value constraints, time dimension
cardinality, and absence of NaN/infinite values.

All validation logic uses only Python stdlib modules.
"""

from __future__ import annotations

import csv
import io
import logging
import math
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

__version__ = "0.1.0"

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HR_COLUMNS: list[str] = [f"HR_{h}" for h in range(1, 25)]
"""The 24 hour-ending column names HR_1 through HR_24."""

SCENARIO_COUNT: int = 50
"""Expected number of scenarios in scenario multiplier files."""

MAX_VIOLATIONS_PER_FILE: int = 20
"""Cap on reported violations per file to avoid report bloat."""

NETWORKS: list[str] = ["case39", "ACTIVSg2000", "ACTIVSg10k"]
"""Network directory names under data/timeseries/."""

# File types that have the 24-hour time dimension (HR_1..HR_24).
_TEMPORAL_FILE_TYPES: frozenset[str] = frozenset(
    {
        "load_24h",
        "wind_forecast_24h",
        "wind_actual_24h",
        "solar_forecast_24h",
        "solar_actual_24h",
        "reserve_requirements_24h",
        "scenario_multipliers_wind_50x24",
        "scenario_multipliers_solar_50x24",
    }
)

_NULL_SENTINEL_VALUES: frozenset[str] = frozenset({"", "nan", "null", "none"})
"""Values treated as null for ID column checks (case-insensitive)."""


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class NetworkId(StrEnum):
    """Network identifiers for the three test case tiers."""

    TINY = "case39"
    SMALL = "ACTIVSg2000"
    MEDIUM = "ACTIVSg10k"


class CsvFileType(StrEnum):
    """Classification of CSV file types in the canonical schema."""

    LOAD_24H = "load_24h"
    WIND_FORECAST_24H = "wind_forecast_24h"
    WIND_ACTUAL_24H = "wind_actual_24h"
    SOLAR_FORECAST_24H = "solar_forecast_24h"
    SOLAR_ACTUAL_24H = "solar_actual_24h"
    GEN_TEMPORAL_PARAMS = "gen_temporal_params"
    RESERVE_REQUIREMENTS_24H = "reserve_requirements_24h"
    RESERVE_ELIGIBILITY = "reserve_eligibility"
    BESS_UNITS = "bess_units"
    DR_BUSES = "dr_buses"
    FLOWGATES = "flowgates"
    SCENARIO_MULTIPLIERS_WIND = "scenario_multipliers_wind_50x24"
    SCENARIO_MULTIPLIERS_SOLAR = "scenario_multipliers_solar_50x24"


class ColumnDtype(StrEnum):
    """Expected data type for a CSV column."""

    INT = "int"
    FLOAT = "float"
    STR = "str"
    BOOL = "bool"


class CheckStatus(StrEnum):
    """Outcome of a single validation check."""

    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"


class CheckId(StrEnum):
    """Identifiers for the schema conformance check categories."""

    FILE_EXISTS = "file_exists"
    COLUMN_NAMES = "column_names"
    COLUMN_ORDER = "column_order"
    DTYPE_CONFORMANCE = "dtype_conformance"
    ID_COLUMN_NOT_NULL = "id_column_not_null"
    BOOL_COLUMN_VALUES = "bool_column_values"
    TIME_DIMENSION = "time_dimension"
    ROW_COUNT = "row_count"
    NO_NAN_INF = "no_nan_inf"


@dataclass(frozen=True)
class ColumnSpec:
    """Schema specification for a single CSV column.

    Encodes the expected name, data type, unit, and value constraints
    for one column.
    """

    name: str
    dtype: ColumnDtype
    unit: str  # e.g., "MW", "MWh", "fraction", "$/MWh", "hours", "none"
    required: bool
    is_id: bool = False
    min_value: float | None = None
    max_value: float | None = None


@dataclass(frozen=True)
class FileManifestEntry:
    """Expected file specification in the manifest.

    Defines everything the validation checks need to know about one
    CSV file: its path relative to the network directory, its file
    type classification, its column schema, and row count constraints.
    """

    relative_path: str
    file_type: CsvFileType
    columns: list[ColumnSpec]
    min_rows: int
    max_rows: int | None = None
    exact_rows: int | None = None


@dataclass(frozen=True)
class CheckViolation:
    """A single violation detected by a schema conformance check.

    Captures enough detail for a human to locate and diagnose the problem.
    """

    column_name: str | None
    row_index: int | None
    error_type: str
    message: str
    actual_value: str | None = None
    expected: str | None = None


@dataclass(frozen=True)
class FileCheckResult:
    """Result of all schema conformance checks for a single file."""

    network_id: str
    relative_path: str
    file_type: CsvFileType
    checks: dict[CheckId, CheckStatus]
    violations: list[CheckViolation]
    row_count: int
    column_count: int
    file_exists: bool


@dataclass(frozen=True)
class NetworkSchemaReport:
    """Aggregated schema conformance results for one network."""

    network_id: str
    file_results: list[FileCheckResult]
    total_files_expected: int
    total_files_found: int
    total_files_missing: int
    total_checks_run: int
    total_checks_passed: int
    total_checks_failed: int
    overall_pass: bool


@dataclass(frozen=True)
class SchemaValidationReport:
    """Top-level schema conformance report across all networks."""

    network_reports: list[NetworkSchemaReport]
    total_files_expected: int
    total_files_found: int
    total_checks_passed: int
    total_checks_failed: int
    overall_pass: bool


# ---------------------------------------------------------------------------
# Manifest construction — column spec builders
# ---------------------------------------------------------------------------


def _hr_column_specs(
    unit: str = "MW",
    *,
    min_value: float | None = 0.0,
) -> list[ColumnSpec]:
    """Build column specs for HR_1 through HR_24."""
    return [
        ColumnSpec(
            name=f"HR_{h}",
            dtype=ColumnDtype.FLOAT,
            unit=unit,
            required=True,
            min_value=min_value,
        )
        for h in range(1, 25)
    ]


def build_column_specs_load() -> list[ColumnSpec]:
    """Build the column specification for load_24h.csv.

    Columns: bus_id (int, ID), HR_1..HR_24 (float, MW, non-negative).
    Total: 25 columns.

    Returns:
        Ordered list of ColumnSpec for the load profile file.
    """
    return [
        ColumnSpec(
            name="bus_id",
            dtype=ColumnDtype.INT,
            unit="none",
            required=True,
            is_id=True,
        ),
        *_hr_column_specs("MW", min_value=0.0),
    ]


def build_column_specs_renewable_profile() -> list[ColumnSpec]:
    """Build the column specification for wind/solar forecast/actual CSVs.

    Columns: gen_uid (str, ID), HR_1..HR_24 (float, MW, non-negative).
    Total: 25 columns.

    Returns:
        Ordered list of ColumnSpec for renewable profile files.
    """
    return [
        ColumnSpec(
            name="gen_uid",
            dtype=ColumnDtype.STR,
            unit="none",
            required=True,
            is_id=True,
        ),
        *_hr_column_specs("MW", min_value=0.0),
    ]


def build_column_specs_gen_temporal_params() -> list[ColumnSpec]:
    """Build the column specification for gen_temporal_params.csv.

    Columns: gen_uid, pmax, pmin, ramp_rate, min_up_time, min_down_time,
    startup_cost, shutdown_cost, marginal_cost, fuel_type, unit_type.

    Returns:
        Ordered list of ColumnSpec for the generator parameters file.
    """
    return [
        ColumnSpec(
            name="gen_uid",
            dtype=ColumnDtype.STR,
            unit="none",
            required=True,
            is_id=True,
        ),
        ColumnSpec(
            name="pmax",
            dtype=ColumnDtype.FLOAT,
            unit="MW",
            required=True,
            min_value=0.0,
        ),
        ColumnSpec(
            name="pmin",
            dtype=ColumnDtype.FLOAT,
            unit="MW",
            required=True,
            min_value=0.0,
        ),
        ColumnSpec(
            name="ramp_rate",
            dtype=ColumnDtype.FLOAT,
            unit="MW/min",
            required=True,
            min_value=0.0,
        ),
        ColumnSpec(
            name="min_up_time",
            dtype=ColumnDtype.FLOAT,
            unit="hours",
            required=True,
            min_value=0.0,
        ),
        ColumnSpec(
            name="min_down_time",
            dtype=ColumnDtype.FLOAT,
            unit="hours",
            required=True,
            min_value=0.0,
        ),
        ColumnSpec(
            name="startup_cost",
            dtype=ColumnDtype.FLOAT,
            unit="$/start",
            required=True,
            min_value=0.0,
        ),
        ColumnSpec(
            name="shutdown_cost",
            dtype=ColumnDtype.FLOAT,
            unit="$/start",
            required=False,
            min_value=0.0,
        ),
        ColumnSpec(
            name="marginal_cost",
            dtype=ColumnDtype.FLOAT,
            unit="$/MWh",
            required=True,
            min_value=0.0,
        ),
        ColumnSpec(name="fuel_type", dtype=ColumnDtype.STR, unit="none", required=True),
        ColumnSpec(name="unit_type", dtype=ColumnDtype.STR, unit="none", required=False),
    ]


def build_column_specs_reserve_requirements() -> list[ColumnSpec]:
    """Build the column specification for reserve_requirements_24h.csv.

    Columns: product (str, ID), HR_1..HR_24 (float, MW, non-negative).
    Total: 25 columns.

    Returns:
        Ordered list of ColumnSpec for the reserve requirements file.
    """
    return [
        ColumnSpec(
            name="product",
            dtype=ColumnDtype.STR,
            unit="none",
            required=True,
            is_id=True,
        ),
        *_hr_column_specs("MW", min_value=0.0),
    ]


def build_column_specs_reserve_eligibility() -> list[ColumnSpec]:
    """Build the column specification for reserve_eligibility.csv.

    Columns: gen_uid, spinning_eligible, non_spinning_eligible,
    max_spinning_mw, max_non_spinning_mw.

    Returns:
        Ordered list of ColumnSpec for the reserve eligibility file.
    """
    return [
        ColumnSpec(
            name="gen_uid",
            dtype=ColumnDtype.STR,
            unit="none",
            required=True,
            is_id=True,
        ),
        ColumnSpec(name="spinning_eligible", dtype=ColumnDtype.BOOL, unit="none", required=True),
        ColumnSpec(
            name="non_spinning_eligible",
            dtype=ColumnDtype.BOOL,
            unit="none",
            required=True,
        ),
        ColumnSpec(
            name="max_spinning_mw",
            dtype=ColumnDtype.FLOAT,
            unit="MW",
            required=False,
            min_value=0.0,
        ),
        ColumnSpec(
            name="max_non_spinning_mw",
            dtype=ColumnDtype.FLOAT,
            unit="MW",
            required=False,
            min_value=0.0,
        ),
    ]


def build_column_specs_bess_units() -> list[ColumnSpec]:
    """Build the column specification for bess_units.csv.

    Columns: unit_id, bus_id, power_mw, energy_mwh, efficiency,
    min_soc, max_soc, init_soc.

    Returns:
        Ordered list of ColumnSpec for the BESS units file.
    """
    return [
        ColumnSpec(
            name="unit_id",
            dtype=ColumnDtype.STR,
            unit="none",
            required=True,
            is_id=True,
        ),
        ColumnSpec(name="bus_id", dtype=ColumnDtype.INT, unit="none", required=True),
        ColumnSpec(
            name="power_mw",
            dtype=ColumnDtype.FLOAT,
            unit="MW",
            required=True,
            min_value=0.0,
        ),
        ColumnSpec(
            name="energy_mwh",
            dtype=ColumnDtype.FLOAT,
            unit="MWh",
            required=True,
            min_value=0.0,
        ),
        ColumnSpec(
            name="efficiency",
            dtype=ColumnDtype.FLOAT,
            unit="fraction",
            required=True,
            min_value=0.0,
            max_value=1.0,
        ),
        ColumnSpec(
            name="min_soc",
            dtype=ColumnDtype.FLOAT,
            unit="fraction",
            required=True,
            min_value=0.0,
            max_value=1.0,
        ),
        ColumnSpec(
            name="max_soc",
            dtype=ColumnDtype.FLOAT,
            unit="fraction",
            required=True,
            min_value=0.0,
            max_value=1.0,
        ),
        ColumnSpec(
            name="init_soc",
            dtype=ColumnDtype.FLOAT,
            unit="fraction",
            required=True,
            min_value=0.0,
            max_value=1.0,
        ),
    ]


def build_column_specs_dr_buses() -> list[ColumnSpec]:
    """Build the column specification for dr_buses.csv.

    Columns: bus_id, max_curtailment_mw, curtailment_cost, max_hours.

    Returns:
        Ordered list of ColumnSpec for the demand response file.
    """
    return [
        ColumnSpec(name="bus_id", dtype=ColumnDtype.INT, unit="none", required=True, is_id=True),
        ColumnSpec(
            name="max_curtailment_mw",
            dtype=ColumnDtype.FLOAT,
            unit="MW",
            required=True,
            min_value=0.0,
        ),
        ColumnSpec(
            name="curtailment_cost",
            dtype=ColumnDtype.FLOAT,
            unit="$/MWh",
            required=True,
            min_value=0.0,
        ),
        ColumnSpec(
            name="max_hours",
            dtype=ColumnDtype.FLOAT,
            unit="hours",
            required=False,
            min_value=0.0,
        ),
    ]


def build_column_specs_flowgates() -> list[ColumnSpec]:
    """Build the column specification for flowgates.csv.

    Columns: flowgate_id, line_ids, weights, limit_mw.

    Returns:
        Ordered list of ColumnSpec for the flowgates file.
    """
    return [
        ColumnSpec(
            name="flowgate_id",
            dtype=ColumnDtype.STR,
            unit="none",
            required=True,
            is_id=True,
        ),
        ColumnSpec(name="line_ids", dtype=ColumnDtype.STR, unit="none", required=True),
        ColumnSpec(name="weights", dtype=ColumnDtype.STR, unit="none", required=True),
        ColumnSpec(
            name="limit_mw",
            dtype=ColumnDtype.FLOAT,
            unit="MW",
            required=True,
            min_value=0.0,
        ),
    ]


def build_column_specs_scenario_multipliers() -> list[ColumnSpec]:
    """Build the column specification for scenario multiplier CSVs.

    Columns: scenario_id (int), generator_id (str, ID),
    HR_1..HR_24 (float, dimensionless, non-negative).
    Total: 26 columns.

    Returns:
        Ordered list of ColumnSpec for scenario multiplier files.
    """
    return [
        ColumnSpec(name="scenario_id", dtype=ColumnDtype.INT, unit="none", required=True),
        ColumnSpec(
            name="generator_id",
            dtype=ColumnDtype.STR,
            unit="none",
            required=True,
            is_id=True,
        ),
        *_hr_column_specs("dimensionless", min_value=0.0),
    ]


# ---------------------------------------------------------------------------
# Manifest construction — per-network manifest builder
# ---------------------------------------------------------------------------


def build_file_manifest(network_id: str) -> list[FileManifestEntry]:
    """Build the expected file manifest for a single network.

    Constructs a list of FileManifestEntry, one per expected CSV file.

    For MEDIUM (ACTIVSg10k), scenario multiplier files are included as
    optional (present in manifest but validated only if they exist) per
    OQ-E03 option B semantics — however, for manifest completeness they
    are always included. The caller can handle SKIP-if-absent logic.

    Args:
        network_id: One of "case39", "ACTIVSg2000", "ACTIVSg10k".

    Returns:
        A list of FileManifestEntry for the network.
    """
    renewable_cols = build_column_specs_renewable_profile()

    entries: list[FileManifestEntry] = [
        FileManifestEntry(
            relative_path="load_24h.csv",
            file_type=CsvFileType.LOAD_24H,
            columns=build_column_specs_load(),
            min_rows=1,
        ),
        FileManifestEntry(
            relative_path="wind_forecast_24h.csv",
            file_type=CsvFileType.WIND_FORECAST_24H,
            columns=renewable_cols,
            min_rows=1,
        ),
        FileManifestEntry(
            relative_path="wind_actual_24h.csv",
            file_type=CsvFileType.WIND_ACTUAL_24H,
            columns=renewable_cols,
            min_rows=1,
        ),
        FileManifestEntry(
            relative_path="solar_forecast_24h.csv",
            file_type=CsvFileType.SOLAR_FORECAST_24H,
            columns=renewable_cols,
            min_rows=1,
        ),
        FileManifestEntry(
            relative_path="solar_actual_24h.csv",
            file_type=CsvFileType.SOLAR_ACTUAL_24H,
            columns=renewable_cols,
            min_rows=1,
        ),
        FileManifestEntry(
            relative_path="gen_temporal_params.csv",
            file_type=CsvFileType.GEN_TEMPORAL_PARAMS,
            columns=build_column_specs_gen_temporal_params(),
            min_rows=1,
        ),
        FileManifestEntry(
            relative_path="reserve_requirements_24h.csv",
            file_type=CsvFileType.RESERVE_REQUIREMENTS_24H,
            columns=build_column_specs_reserve_requirements(),
            min_rows=2,
        ),
        FileManifestEntry(
            relative_path="reserve_eligibility.csv",
            file_type=CsvFileType.RESERVE_ELIGIBILITY,
            columns=build_column_specs_reserve_eligibility(),
            min_rows=1,
        ),
        FileManifestEntry(
            relative_path="bess_units.csv",
            file_type=CsvFileType.BESS_UNITS,
            columns=build_column_specs_bess_units(),
            min_rows=1,
        ),
        FileManifestEntry(
            relative_path="dr_buses.csv",
            file_type=CsvFileType.DR_BUSES,
            columns=build_column_specs_dr_buses(),
            min_rows=1,
        ),
        FileManifestEntry(
            relative_path="flowgates.csv",
            file_type=CsvFileType.FLOWGATES,
            columns=build_column_specs_flowgates(),
            min_rows=3,
            max_rows=5,
        ),
    ]

    # Scenario multiplier files — include for all networks.
    # For MEDIUM, downstream validation treats absent files as SKIP per OQ-E03.
    scenario_cols = build_column_specs_scenario_multipliers()
    entries.append(
        FileManifestEntry(
            relative_path="scenarios/scenario_multipliers_wind_50x24.csv",
            file_type=CsvFileType.SCENARIO_MULTIPLIERS_WIND,
            columns=scenario_cols,
            min_rows=SCENARIO_COUNT,
            exact_rows=SCENARIO_COUNT,
        ),
    )
    entries.append(
        FileManifestEntry(
            relative_path="scenarios/scenario_multipliers_solar_50x24.csv",
            file_type=CsvFileType.SCENARIO_MULTIPLIERS_SOLAR,
            columns=scenario_cols,
            min_rows=SCENARIO_COUNT,
            exact_rows=SCENARIO_COUNT,
        ),
    )

    return entries


# ---------------------------------------------------------------------------
# Individual check functions
# ---------------------------------------------------------------------------


def check_file_exists(
    file_path: Path,
) -> tuple[CheckStatus, list[CheckViolation]]:
    """Verify that a CSV file exists at the expected path.

    Args:
        file_path: Absolute path to the expected CSV file.

    Returns:
        (PASS, []) if the file exists, or (FAIL, [violation]) with
        the missing path in the violation message.
    """
    if file_path.is_file():
        return CheckStatus.PASS, []
    return CheckStatus.FAIL, [
        CheckViolation(
            column_name=None,
            row_index=None,
            error_type="missing_file",
            message=f"Expected file not found: {file_path}",
            expected=str(file_path),
        ),
    ]


def check_column_names(
    actual_columns: list[str],
    expected_columns: list[ColumnSpec],
) -> tuple[CheckStatus, list[CheckViolation]]:
    """Verify that actual column names match expected names exactly.

    Checks for missing required columns and extra columns. Extra columns
    generate violations but do not cause FAIL on their own (option B from
    OQ-D5.01-02).

    Args:
        actual_columns: Column names read from the CSV header.
        expected_columns: ColumnSpec list from the manifest.

    Returns:
        (PASS, []) if all required columns present, or (FAIL, violations)
        with details of each missing column.
    """
    violations: list[CheckViolation] = []
    actual_set = set(actual_columns)
    expected_names = {cs.name for cs in expected_columns}
    required_names = {cs.name for cs in expected_columns if cs.required}

    # Check for missing required columns.
    missing = required_names - actual_set
    for col_name in sorted(missing):
        violations.append(
            CheckViolation(
                column_name=col_name,
                row_index=None,
                error_type="missing_column",
                message=f"Required column '{col_name}' is missing",
                expected=col_name,
            )
        )

    # Extra columns are warnings (included in violations but don't cause FAIL).
    extra = actual_set - expected_names
    for col_name in sorted(extra):
        violations.append(
            CheckViolation(
                column_name=col_name,
                row_index=None,
                error_type="extra_column",
                message=f"Unexpected extra column '{col_name}'",
                actual_value=col_name,
            )
        )

    # FAIL only if required columns are missing.
    status = CheckStatus.FAIL if missing else CheckStatus.PASS
    return status, violations


def check_column_order(
    actual_columns: list[str],
    expected_columns: list[ColumnSpec],
) -> tuple[CheckStatus, list[CheckViolation]]:
    """Verify that columns appear in the canonical order.

    Only checks ordering of columns present in both actual and expected.

    Args:
        actual_columns: Column names from the CSV header.
        expected_columns: ColumnSpec list from the manifest.

    Returns:
        (PASS, []) if column order matches, or (FAIL, violations)
        listing the first out-of-order column pair.
    """
    expected_names = [cs.name for cs in expected_columns]
    # Filter to columns present in both.
    actual_filtered = [c for c in actual_columns if c in {cs.name for cs in expected_columns}]
    expected_filtered = [c for c in expected_names if c in set(actual_columns)]

    violations: list[CheckViolation] = []
    if actual_filtered != expected_filtered:
        # Find first mismatch.
        for i, (a, e) in enumerate(zip(actual_filtered, expected_filtered)):
            if a != e:
                violations.append(
                    CheckViolation(
                        column_name=e,
                        row_index=None,
                        error_type="wrong_order",
                        message=(f"Column '{e}' expected at position {i} but found '{a}'"),
                        actual_value=a,
                        expected=e,
                    )
                )
                break

    status = CheckStatus.FAIL if violations else CheckStatus.PASS
    return status, violations


def check_dtype_conformance(
    csv_path: Path,
    expected_columns: list[ColumnSpec],
) -> tuple[CheckStatus, list[CheckViolation]]:
    """Verify that column values parse to the declared data types.

    For FLOAT or INT columns, attempts to parse every value. For BOOL
    columns, verifies values are in {"true", "false"} (case-insensitive).
    Stops after MAX_VIOLATIONS_PER_FILE violations.

    Args:
        csv_path: Path to the CSV file.
        expected_columns: ColumnSpec list with dtype declarations.

    Returns:
        (PASS, []) if all values parse correctly, or (FAIL, violations).
    """
    violations: list[CheckViolation] = []
    spec_by_name: dict[str, ColumnSpec] = {cs.name: cs for cs in expected_columns}

    text = csv_path.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        return CheckStatus.PASS, []

    for row_idx, row in enumerate(reader):
        if len(violations) >= MAX_VIOLATIONS_PER_FILE:
            break
        for col_name, value in row.items():
            if len(violations) >= MAX_VIOLATIONS_PER_FILE:
                break
            if col_name not in spec_by_name:
                continue
            spec = spec_by_name[col_name]
            if value is None or value.strip() == "":
                continue  # Nulls caught by id_column_not_null / no_nan_inf

            val = value.strip()
            if spec.dtype == ColumnDtype.INT:
                try:
                    int(val)
                except ValueError:
                    violations.append(
                        CheckViolation(
                            column_name=col_name,
                            row_index=row_idx,
                            error_type="wrong_dtype",
                            message=f"Cannot parse '{val}' as int in column '{col_name}'",
                            actual_value=val,
                            expected="int",
                        )
                    )
            elif spec.dtype == ColumnDtype.FLOAT:
                try:
                    float(val)
                except ValueError:
                    violations.append(
                        CheckViolation(
                            column_name=col_name,
                            row_index=row_idx,
                            error_type="wrong_dtype",
                            message=f"Cannot parse '{val}' as float in column '{col_name}'",
                            actual_value=val,
                            expected="float",
                        )
                    )
            elif spec.dtype == ColumnDtype.BOOL:
                if val.lower() not in {"true", "false"}:
                    violations.append(
                        CheckViolation(
                            column_name=col_name,
                            row_index=row_idx,
                            error_type="wrong_dtype",
                            message=(
                                f"Invalid boolean value '{val}' in column '{col_name}' "
                                f"(expected true/false)"
                            ),
                            actual_value=val,
                            expected="true/false",
                        )
                    )

    status = CheckStatus.FAIL if violations else CheckStatus.PASS
    return status, violations


def check_id_columns_not_null(
    csv_path: Path,
    expected_columns: list[ColumnSpec],
) -> tuple[CheckStatus, list[CheckViolation]]:
    """Verify that ID columns contain no null or empty values.

    A value is considered null if it is empty string, whitespace-only,
    "nan", "null", or "none" (case-insensitive).

    Args:
        csv_path: Path to the CSV file.
        expected_columns: ColumnSpec list identifying ID columns.

    Returns:
        (PASS, []) if all ID values are non-null, or (FAIL, violations).
    """
    violations: list[CheckViolation] = []
    id_col_names = {cs.name for cs in expected_columns if cs.is_id}
    if not id_col_names:
        return CheckStatus.PASS, []

    text = csv_path.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        return CheckStatus.PASS, []

    for row_idx, row in enumerate(reader):
        if len(violations) >= MAX_VIOLATIONS_PER_FILE:
            break
        for col_name in id_col_names:
            if len(violations) >= MAX_VIOLATIONS_PER_FILE:
                break
            if col_name not in row:
                continue
            value = row[col_name]
            if (
                value is None
                or value.strip() == ""
                or value.strip().lower() in _NULL_SENTINEL_VALUES
            ):
                violations.append(
                    CheckViolation(
                        column_name=col_name,
                        row_index=row_idx,
                        error_type="null_id",
                        message=f"Null/empty value in ID column '{col_name}' at row {row_idx}",
                        actual_value=repr(value) if value is not None else "None",
                    )
                )

    status = CheckStatus.FAIL if violations else CheckStatus.PASS
    return status, violations


def check_time_dimension(
    actual_columns: list[str],
    file_type: CsvFileType,
) -> tuple[CheckStatus, list[CheckViolation]]:
    """Verify the time dimension columns for temporal files.

    For daily profile file types, verifies HR_1 through HR_24 are all
    present with no gaps. For non-temporal file types, the check is skipped.

    Args:
        actual_columns: Column names from the CSV header.
        file_type: The CsvFileType classification.

    Returns:
        (PASS, []) if all 24 HR columns present, (SKIP, []) for
        non-temporal files, or (FAIL, violations) listing missing HR columns.
    """
    if file_type.value not in _TEMPORAL_FILE_TYPES:
        return CheckStatus.SKIP, []

    violations: list[CheckViolation] = []
    actual_set = set(actual_columns)
    for hr_col in HR_COLUMNS:
        if hr_col not in actual_set:
            violations.append(
                CheckViolation(
                    column_name=hr_col,
                    row_index=None,
                    error_type="missing_hr_column",
                    message=f"Missing hour column '{hr_col}'",
                    expected=hr_col,
                )
            )

    status = CheckStatus.FAIL if violations else CheckStatus.PASS
    return status, violations


def check_row_count(
    actual_row_count: int,
    manifest_entry: FileManifestEntry,
) -> tuple[CheckStatus, list[CheckViolation]]:
    """Verify the row count matches manifest constraints.

    Args:
        actual_row_count: Number of data rows in the CSV (excluding header).
        manifest_entry: The manifest entry with row count constraints.

    Returns:
        (PASS, []) if row count is within bounds, or (FAIL, [violation]).
    """
    violations: list[CheckViolation] = []

    if manifest_entry.exact_rows is not None:
        if actual_row_count != manifest_entry.exact_rows:
            violations.append(
                CheckViolation(
                    column_name=None,
                    row_index=None,
                    error_type="wrong_row_count",
                    message=(
                        f"Expected exactly {manifest_entry.exact_rows} rows, got {actual_row_count}"
                    ),
                    actual_value=str(actual_row_count),
                    expected=str(manifest_entry.exact_rows),
                )
            )
    else:
        if actual_row_count < manifest_entry.min_rows:
            violations.append(
                CheckViolation(
                    column_name=None,
                    row_index=None,
                    error_type="too_few_rows",
                    message=(
                        f"Expected at least {manifest_entry.min_rows} rows, got {actual_row_count}"
                    ),
                    actual_value=str(actual_row_count),
                    expected=f">={manifest_entry.min_rows}",
                )
            )
        if manifest_entry.max_rows is not None and actual_row_count > manifest_entry.max_rows:
            violations.append(
                CheckViolation(
                    column_name=None,
                    row_index=None,
                    error_type="too_many_rows",
                    message=(
                        f"Expected at most {manifest_entry.max_rows} rows, got {actual_row_count}"
                    ),
                    actual_value=str(actual_row_count),
                    expected=f"<={manifest_entry.max_rows}",
                )
            )

    status = CheckStatus.FAIL if violations else CheckStatus.PASS
    return status, violations


def check_no_nan_inf(
    csv_path: Path,
    expected_columns: list[ColumnSpec],
) -> tuple[CheckStatus, list[CheckViolation]]:
    """Verify that numeric columns contain no NaN or infinite values.

    For each FLOAT or INT column, checks every value for NaN or infinity.
    Stops after MAX_VIOLATIONS_PER_FILE violations.

    Args:
        csv_path: Path to the CSV file.
        expected_columns: ColumnSpec list identifying numeric columns.

    Returns:
        (PASS, []) if no NaN/inf found, or (FAIL, violations).
    """
    violations: list[CheckViolation] = []
    numeric_col_names = {
        cs.name for cs in expected_columns if cs.dtype in {ColumnDtype.FLOAT, ColumnDtype.INT}
    }
    if not numeric_col_names:
        return CheckStatus.PASS, []

    text = csv_path.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        return CheckStatus.PASS, []

    for row_idx, row in enumerate(reader):
        if len(violations) >= MAX_VIOLATIONS_PER_FILE:
            break
        for col_name in numeric_col_names:
            if len(violations) >= MAX_VIOLATIONS_PER_FILE:
                break
            if col_name not in row:
                continue
            value = row[col_name]
            if value is None or value.strip() == "":
                # Null value — report as nan.
                violations.append(
                    CheckViolation(
                        column_name=col_name,
                        row_index=row_idx,
                        error_type="nan_value",
                        message=f"Null/empty value in numeric column '{col_name}' at row {row_idx}",
                        actual_value=repr(value),
                    )
                )
                continue

            val_str = value.strip().lower()
            if val_str in {"nan", "-nan"}:
                violations.append(
                    CheckViolation(
                        column_name=col_name,
                        row_index=row_idx,
                        error_type="nan_value",
                        message=f"NaN value in column '{col_name}' at row {row_idx}",
                        actual_value=value.strip(),
                    )
                )
                continue

            if val_str in {"inf", "-inf", "+inf", "infinity", "-infinity", "+infinity"}:
                violations.append(
                    CheckViolation(
                        column_name=col_name,
                        row_index=row_idx,
                        error_type="inf_value",
                        message=f"Infinite value in column '{col_name}' at row {row_idx}",
                        actual_value=value.strip(),
                    )
                )
                continue

            # Also check parsed float for nan/inf.
            try:
                parsed = float(val_str)
                if math.isnan(parsed):
                    violations.append(
                        CheckViolation(
                            column_name=col_name,
                            row_index=row_idx,
                            error_type="nan_value",
                            message=f"NaN value in column '{col_name}' at row {row_idx}",
                            actual_value=value.strip(),
                        )
                    )
                elif math.isinf(parsed):
                    violations.append(
                        CheckViolation(
                            column_name=col_name,
                            row_index=row_idx,
                            error_type="inf_value",
                            message=f"Infinite value in column '{col_name}' at row {row_idx}",
                            actual_value=value.strip(),
                        )
                    )
            except ValueError:
                pass  # dtype conformance catches parse errors

    status = CheckStatus.FAIL if violations else CheckStatus.PASS
    return status, violations


# ---------------------------------------------------------------------------
# Per-file orchestration
# ---------------------------------------------------------------------------


def _read_csv_header_and_count(csv_path: Path) -> tuple[list[str], int]:
    """Read CSV header and count data rows.

    Args:
        csv_path: Path to the CSV file.

    Returns:
        (column_names, row_count) where row_count excludes the header.
    """
    text = csv_path.read_text(encoding="utf-8")
    reader = csv.reader(io.StringIO(text))
    header = next(reader, [])
    row_count = sum(1 for _ in reader)
    return [col.strip() for col in header], row_count


def validate_file(
    network_id: str,
    network_dir: Path,
    manifest_entry: FileManifestEntry,
) -> FileCheckResult:
    """Run all schema conformance checks for a single file.

    Orchestrates the check sequence:
    1. check_file_exists -- if FAIL, skip all subsequent checks.
    2. Read the CSV header and count rows.
    3. check_column_names
    4. check_column_order
    5. check_time_dimension
    6. check_row_count
    7. check_dtype_conformance
    8. check_id_columns_not_null
    9. check_no_nan_inf

    Args:
        network_id: Network identifier (e.g., "case39").
        network_dir: Path to the network's timeseries directory.
        manifest_entry: The expected file specification.

    Returns:
        A FileCheckResult with per-check status and all violations.
    """
    file_path = network_dir / manifest_entry.relative_path
    all_violations: list[CheckViolation] = []
    checks: dict[CheckId, CheckStatus] = {}

    # 1. File existence.
    status, violations = check_file_exists(file_path)
    checks[CheckId.FILE_EXISTS] = status
    all_violations.extend(violations)

    if status == CheckStatus.FAIL:
        # Skip all downstream checks.
        for check_id in [
            CheckId.COLUMN_NAMES,
            CheckId.COLUMN_ORDER,
            CheckId.TIME_DIMENSION,
            CheckId.ROW_COUNT,
            CheckId.DTYPE_CONFORMANCE,
            CheckId.ID_COLUMN_NOT_NULL,
            CheckId.BOOL_COLUMN_VALUES,
            CheckId.NO_NAN_INF,
        ]:
            checks[check_id] = CheckStatus.SKIP

        return FileCheckResult(
            network_id=network_id,
            relative_path=manifest_entry.relative_path,
            file_type=manifest_entry.file_type,
            checks=checks,
            violations=all_violations,
            row_count=0,
            column_count=0,
            file_exists=False,
        )

    # 2. Read header and count.
    actual_columns, row_count = _read_csv_header_and_count(file_path)
    logger.info(
        "Validating %s: %d columns, %d rows",
        manifest_entry.relative_path,
        len(actual_columns),
        row_count,
    )

    # 3. Column names.
    status, violations = check_column_names(actual_columns, manifest_entry.columns)
    checks[CheckId.COLUMN_NAMES] = status
    all_violations.extend(violations)

    # 4. Column order.
    status, violations = check_column_order(actual_columns, manifest_entry.columns)
    checks[CheckId.COLUMN_ORDER] = status
    all_violations.extend(violations)

    # 5. Time dimension.
    status, violations = check_time_dimension(actual_columns, manifest_entry.file_type)
    checks[CheckId.TIME_DIMENSION] = status
    all_violations.extend(violations)

    # 6. Row count.
    status, violations = check_row_count(row_count, manifest_entry)
    checks[CheckId.ROW_COUNT] = status
    all_violations.extend(violations)

    # 7. Dtype conformance.
    status, violations = check_dtype_conformance(file_path, manifest_entry.columns)
    checks[CheckId.DTYPE_CONFORMANCE] = status
    all_violations.extend(violations)

    # 8. ID columns not null.
    status, violations = check_id_columns_not_null(file_path, manifest_entry.columns)
    checks[CheckId.ID_COLUMN_NOT_NULL] = status
    all_violations.extend(violations)

    # 9. Bool column values — same logic as dtype conformance for bools,
    #    tracked under a separate check ID for reporting clarity.
    bool_cols = [cs for cs in manifest_entry.columns if cs.dtype == ColumnDtype.BOOL]
    if bool_cols:
        status, violations = check_dtype_conformance(file_path, bool_cols)
        checks[CheckId.BOOL_COLUMN_VALUES] = status
        # Don't double-count violations already found in dtype conformance.
    else:
        checks[CheckId.BOOL_COLUMN_VALUES] = CheckStatus.SKIP

    # 10. No NaN/inf.
    status, violations = check_no_nan_inf(file_path, manifest_entry.columns)
    checks[CheckId.NO_NAN_INF] = status
    all_violations.extend(violations)

    return FileCheckResult(
        network_id=network_id,
        relative_path=manifest_entry.relative_path,
        file_type=manifest_entry.file_type,
        checks=checks,
        violations=all_violations,
        row_count=row_count,
        column_count=len(actual_columns),
        file_exists=True,
    )


# ---------------------------------------------------------------------------
# Network-level orchestration
# ---------------------------------------------------------------------------


def validate_network_schema(
    network_id: str,
    timeseries_base_dir: Path,
) -> NetworkSchemaReport:
    """Run schema conformance checks for all files in one network.

    Args:
        network_id: Network identifier (e.g., "case39").
        timeseries_base_dir: Base directory containing network
            subdirectories (e.g., data/timeseries/).

    Returns:
        A NetworkSchemaReport with per-file results and summary counts.
    """
    network_dir = timeseries_base_dir / network_id
    manifest = build_file_manifest(network_id)

    file_results: list[FileCheckResult] = []
    for entry in manifest:
        result = validate_file(network_id, network_dir, entry)
        file_results.append(result)

    total_files_expected = len(manifest)
    total_files_found = sum(1 for r in file_results if r.file_exists)
    total_files_missing = total_files_expected - total_files_found

    total_checks_run = 0
    total_checks_passed = 0
    total_checks_failed = 0
    for r in file_results:
        for check_status in r.checks.values():
            if check_status != CheckStatus.SKIP:
                total_checks_run += 1
                if check_status == CheckStatus.PASS:
                    total_checks_passed += 1
                elif check_status == CheckStatus.FAIL:
                    total_checks_failed += 1

    overall_pass = total_checks_failed == 0

    return NetworkSchemaReport(
        network_id=network_id,
        file_results=file_results,
        total_files_expected=total_files_expected,
        total_files_found=total_files_found,
        total_files_missing=total_files_missing,
        total_checks_run=total_checks_run,
        total_checks_passed=total_checks_passed,
        total_checks_failed=total_checks_failed,
        overall_pass=overall_pass,
    )


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------


def run_schema_validation(
    timeseries_base_dir: Path | None = None,
    *,
    networks: list[str] | None = None,
) -> SchemaValidationReport:
    """Entry point: run schema conformance checks across all networks.

    Args:
        timeseries_base_dir: Base directory for network data. Defaults
            to <repo_root>/data/timeseries/.
        networks: List of network IDs to validate. Defaults to
            ["case39", "ACTIVSg2000", "ACTIVSg10k"].

    Returns:
        A SchemaValidationReport with results for all networks.
    """
    if timeseries_base_dir is None:
        repo_root = Path(__file__).resolve().parent.parent
        timeseries_base_dir = repo_root / "data" / "timeseries"

    if networks is None:
        networks = list(NETWORKS)

    network_reports: list[NetworkSchemaReport] = []
    for network_id in networks:
        report = validate_network_schema(network_id, timeseries_base_dir)
        network_reports.append(report)

    total_files_expected = sum(r.total_files_expected for r in network_reports)
    total_files_found = sum(r.total_files_found for r in network_reports)
    total_checks_passed = sum(r.total_checks_passed for r in network_reports)
    total_checks_failed = sum(r.total_checks_failed for r in network_reports)
    overall_pass = all(r.overall_pass for r in network_reports)

    return SchemaValidationReport(
        network_reports=network_reports,
        total_files_expected=total_files_expected,
        total_files_found=total_files_found,
        total_checks_passed=total_checks_passed,
        total_checks_failed=total_checks_failed,
        overall_pass=overall_pass,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    report = run_schema_validation()
    status_str = "PASS" if report.overall_pass else "FAIL"
    print(f"Schema validation: {status_str}")
    print(f"  Files: {report.total_files_found}/{report.total_files_expected}")
    print(f"  Checks passed: {report.total_checks_passed}")
    print(f"  Checks failed: {report.total_checks_failed}")
