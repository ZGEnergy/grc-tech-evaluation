"""Intermediate Format Schema Specification for PSS/E v31.

Defines JSON Schema files (one per PSS/E v31 record type table) plus a
top-level manifest schema and a human-readable markdown summary.  The schema
is the central artifact of Phase 1 -- every reference solution, mapping guide,
supplemental CSV join, and per-tool FNM ingestion test flows through it.

Field inventory is hardcoded to PSS/E v31 Program Operation Manual definitions.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from fnm.scripts.raw_record_counter import PSSE_V31_SECTION_NAMES

# ---------------------------------------------------------------------------
# PSS/E v31 record types -- canonical ordering
# ---------------------------------------------------------------------------

PSSE_V31_RECORD_TYPES: tuple[str, ...] = PSSE_V31_SECTION_NAMES
"""All 17 PSS/E v31 record types in section order. Only non-empty types
(as reported by D3) get a table schema in the intermediate format."""


# ---------------------------------------------------------------------------
# Per-unit base classification
# ---------------------------------------------------------------------------


class PerUnitBase(Enum):
    """Classification of a field's per-unit base reference."""

    SYSTEM_MVA = "system_mva"
    WINDING_MVA = "winding_mva"
    BUS_KV = "bus_kv"
    NONE = "none"
    MIXED = "mixed"


# ---------------------------------------------------------------------------
# Field specification
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FieldSpec:
    """Schema specification for a single field in a PSS/E record type."""

    name: str
    data_type: str
    description: str
    required: bool
    per_unit_base: PerUnitBase
    unit: str
    default_value: int | float | str | None
    valid_range: tuple[float | None, float | None] | None
    present_but_inactive: bool = False
    preservation_critical: bool = False


# ---------------------------------------------------------------------------
# Table schema
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TableSchema:
    """Schema specification for one PSS/E record type table."""

    record_type: str
    table_name: str
    description: str
    fields: list[FieldSpec]
    primary_key: list[str]
    multi_line_record: bool = False
    notes: str = ""


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ManifestEntry:
    """Entry for one table in the intermediate format manifest."""

    table_name: str
    record_type: str
    file_name: str
    record_count: int
    column_count: int
    schema_file: str


@dataclass(frozen=True)
class IntermediateFormatManifest:
    """Top-level manifest for the intermediate format."""

    sbase: float
    basfrq: float
    rev: float
    case_id: str
    canonical_parser: str
    tables: list[ManifestEntry]
    total_records: int
    total_tables: int
    non_empty_record_types: list[str]
    schema_version: str = "1.0.0"
    generated_timestamp: str = ""


# ---------------------------------------------------------------------------
# Validation report
# ---------------------------------------------------------------------------


class ConformanceLevel(Enum):
    """Severity level for a conformance finding."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class ConformanceFinding:
    """A single conformance check result."""

    table_name: str
    field_name: str
    level: ConformanceLevel
    message: str
    check_id: str


@dataclass(frozen=True)
class ConformanceReport:
    """Complete validation report for intermediate format tables."""

    tables_checked: int
    tables_expected: int
    errors: list[ConformanceFinding]
    warnings: list[ConformanceFinding]
    info: list[ConformanceFinding]
    is_conformant: bool
    manifest_valid: bool


# ---------------------------------------------------------------------------
# PSS/E v31 Field Inventory -- hardcoded from Program Operation Manual
# ---------------------------------------------------------------------------

_F = FieldSpec
_N = PerUnitBase.NONE
_S = PerUnitBase.SYSTEM_MVA
_B = PerUnitBase.BUS_KV
_M = PerUnitBase.MIXED
_BLANK12 = "            "


def _bus_fields() -> list[FieldSpec]:
    return [
        _F("I", "integer", "Bus number (1-999997)", True, _N, "", None, (1, 999997)),
        _F("NAME", "string", "Bus name (up to 12 chars)", True, _N, "", _BLANK12, None),
        _F("BASKV", "number", "Bus base voltage", True, _N, "kV", 0.0, (0.0, None)),
        _F("IDE", "integer", "Bus type code (1-4)", True, _N, "", 1, (1, 4)),
        _F("AREA", "integer", "Area number", True, _N, "", 1, (1, None)),
        _F("ZONE", "integer", "Zone number", True, _N, "", 1, (1, None)),
        _F("OWNER", "integer", "Owner number", True, _N, "", 1, (1, None)),
        _F("VM", "number", "Bus voltage magnitude", True, _B, "pu", 1.0, (0.0, 2.0)),
        _F("VA", "number", "Bus voltage angle", True, _N, "deg", 0.0, None),
        _F("NVHI", "number", "Normal voltage high limit", False, _B, "pu", 1.1, (0.0, 2.0)),
        _F("NVLO", "number", "Normal voltage low limit", False, _B, "pu", 0.9, (0.0, 2.0)),
        _F("EVHI", "number", "Emergency voltage high limit", False, _B, "pu", 1.1, (0.0, 2.0)),
        _F("EVLO", "number", "Emergency voltage low limit", False, _B, "pu", 0.9, (0.0, 2.0)),
    ]


def _load_fields() -> list[FieldSpec]:
    return [
        _F("I", "integer", "Bus number", True, _N, "", None, None),
        _F("ID", "string", "Load identifier (2 chars)", True, _N, "", "1 ", None),
        _F("STATUS", "integer", "Load status (1=in, 0=out)", True, _N, "", 1, (0, 1)),
        _F("AREA", "integer", "Area number", True, _N, "", 1, None),
        _F("ZONE", "integer", "Zone number", True, _N, "", 1, None),
        _F("PL", "number", "Constant power load (P)", True, _N, "MW", 0.0, None),
        _F("QL", "number", "Constant power load (Q)", True, _N, "MVAR", 0.0, None),
        _F("IP", "number", "Constant current load (P)", False, _N, "MW", 0.0, None),
        _F("IQ", "number", "Constant current load (Q)", False, _N, "MVAR", 0.0, None),
        _F("YP", "number", "Constant admittance load (P)", False, _N, "MW", 0.0, None),
        _F("YQ", "number", "Constant admittance load (Q)", False, _N, "MVAR", 0.0, None),
        _F("OWNER", "integer", "Owner number", False, _N, "", 1, None),
        _F("SCALE", "integer", "Scaling flag (1=yes, 0=no)", False, _N, "", 1, (0, 1)),
    ]


def _fixed_shunt_fields() -> list[FieldSpec]:
    return [
        _F("I", "integer", "Bus number", True, _N, "", None, None),
        _F("ID", "string", "Shunt identifier (2 chars)", True, _N, "", "1 ", None),
        _F("STATUS", "integer", "Status (1=in, 0=out)", True, _N, "", 1, (0, 1)),
        _F("GL", "number", "Shunt conductance", True, _N, "MW", 0.0, None),
        _F("BL", "number", "Shunt susceptance (+cap)", True, _N, "MVAR", 0.0, None),
    ]


def _generator_fields() -> list[FieldSpec]:
    return [
        _F("I", "integer", "Bus number", True, _N, "", None, None),
        _F("ID", "string", "Machine identifier (2 chars)", True, _N, "", "1 ", None),
        _F("PG", "number", "Active power output", True, _N, "MW", 0.0, None),
        _F("QG", "number", "Reactive power output", True, _N, "MVAR", 0.0, None),
        _F("QT", "number", "Max reactive power", True, _N, "MVAR", 9999.0, None),
        _F("QB", "number", "Min reactive power", True, _N, "MVAR", -9999.0, None),
        _F("VS", "number", "Regulated voltage setpoint", True, _B, "pu", 1.0, None),
        _F("IREG", "integer", "Remote regulated bus (0=local)", True, _N, "", 0, None, False, True),
        _F("MBASE", "number", "Machine MVA base", True, _N, "MVA", 100.0, None),
        _F("ZR", "number", "Machine resistance (on MBASE)", False, _S, "pu", 0.0, None),
        _F("ZX", "number", "Machine reactance (on MBASE)", False, _S, "pu", 1.0, None),
        _F("RT", "number", "Step-up xfmr resistance", False, _S, "pu", 0.0, None),
        _F("XT", "number", "Step-up xfmr reactance", False, _S, "pu", 0.0, None),
        _F("GTAP", "number", "Step-up xfmr tap ratio", False, _B, "pu", 1.0, None),
        _F("STAT", "integer", "Status (1=in, 0=out)", True, _N, "", 1, (0, 1)),
        _F("RMPCT", "number", "MVAR range pct for remote reg", False, _N, "%", 100.0, (0.0, 100.0)),
        _F("PT", "number", "Max active power", False, _N, "MW", 9999.0, None),
        _F("PB", "number", "Min active power", False, _N, "MW", -9999.0, None),
        _F("O1", "integer", "Owner 1", False, _N, "", 1, None),
        _F("F1", "number", "Fraction owned by owner 1", False, _N, "", 1.0, (0.0, 1.0)),
        _F("O2", "integer", "Owner 2", False, _N, "", 0, None),
        _F("F2", "number", "Fraction owned by owner 2", False, _N, "", 0.0, (0.0, 1.0)),
        _F("O3", "integer", "Owner 3", False, _N, "", 0, None),
        _F("F3", "number", "Fraction owned by owner 3", False, _N, "", 0.0, (0.0, 1.0)),
        _F("O4", "integer", "Owner 4", False, _N, "", 0, None),
        _F("F4", "number", "Fraction owned by owner 4", False, _N, "", 0.0, (0.0, 1.0)),
        _F("WMOD", "integer", "Wind machine Q control mode", False, _N, "", 0, None),
        _F("WPF", "number", "Wind machine power factor", False, _N, "", 1.0, None),
    ]


def _branch_fields() -> list[FieldSpec]:
    return [
        _F("I", "integer", "From bus number", True, _N, "", None, None),
        _F("J", "integer", "To bus number", True, _N, "", None, None),
        _F("CKT", "string", "Circuit identifier (2 chars)", True, _N, "", "1 ", None),
        _F("R", "number", "Branch resistance", True, _S, "pu", None, None),
        _F("X", "number", "Branch reactance", True, _S, "pu", None, None),
        _F("B", "number", "Branch charging susceptance", True, _S, "pu", 0.0, None),
        _F("RATEA", "number", "Rating A (normal)", True, _N, "MVA", 0.0, None),
        _F("RATEB", "number", "Rating B (emergency)", True, _N, "MVA", 0.0, None),
        _F("RATEC", "number", "Rating C (long-term)", True, _N, "MVA", 0.0, None),
        _F("GI", "number", "Shunt conductance at I", False, _S, "pu", 0.0, None),
        _F("BI", "number", "Shunt susceptance at I", False, _S, "pu", 0.0, None),
        _F("GJ", "number", "Shunt conductance at J", False, _S, "pu", 0.0, None),
        _F("BJ", "number", "Shunt susceptance at J", False, _S, "pu", 0.0, None),
        _F("ST", "integer", "Status (1=in, 0=out)", True, _N, "", 1, (0, 1)),
        _F("MET", "integer", "Metered end (1=I, 2=J)", False, _N, "", 1, (1, 2)),
        _F("LEN", "number", "Line length", False, _N, "", 0.0, None),
        _F("O1", "integer", "Owner 1", False, _N, "", 1, None),
        _F("F1", "number", "Fraction owned by owner 1", False, _N, "", 1.0, (0.0, 1.0)),
        _F("O2", "integer", "Owner 2", False, _N, "", 0, None),
        _F("F2", "number", "Fraction owned by owner 2", False, _N, "", 0.0, (0.0, 1.0)),
        _F("O3", "integer", "Owner 3", False, _N, "", 0, None),
        _F("F3", "number", "Fraction owned by owner 3", False, _N, "", 0.0, (0.0, 1.0)),
        _F("O4", "integer", "Owner 4", False, _N, "", 0, None),
        _F("F4", "number", "Fraction owned by owner 4", False, _N, "", 0.0, (0.0, 1.0)),
    ]


def _transformer_fields() -> list[FieldSpec]:
    """Transformer fields -- all 5 lines flattened."""
    P = True  # preservation_critical  # noqa: N806
    return [
        # Line 1 -- common
        _F("I", "integer", "Winding 1 bus", True, _N, "", None, None),
        _F("J", "integer", "Winding 2 bus", True, _N, "", None, None),
        _F("K", "integer", "Winding 3 bus (0=2W)", True, _N, "", 0, None, False, P),
        _F("CKT", "string", "Circuit identifier", True, _N, "", "1 ", None),
        _F("CW", "integer", "Winding data I/O code", True, _N, "", 1, (1, 3), False, P),
        _F("CZ", "integer", "Impedance data I/O code", True, _N, "", 1, (1, 3), False, P),
        _F("CM", "integer", "Mag admittance I/O code", True, _N, "", 1, (1, 2), False, P),
        _F("MAG1", "number", "Magnetizing conductance", False, _M, "", 0.0, None),
        _F("MAG2", "number", "Magnetizing susceptance", False, _M, "", 0.0, None),
        _F("NMETR", "integer", "Non-metered end code", False, _N, "", 2, None),
        _F("NAME", "string", "Transformer name", False, _N, "", _BLANK12, None),
        _F("STAT", "integer", "Status (0-4)", True, _N, "", 1, (0, 4)),
        _F("O1", "integer", "Owner 1", False, _N, "", 1, None),
        _F("F1", "number", "Fraction by owner 1", False, _N, "", 1.0, (0.0, 1.0)),
        _F("O2", "integer", "Owner 2", False, _N, "", 0, None),
        _F("F2", "number", "Fraction by owner 2", False, _N, "", 0.0, (0.0, 1.0)),
        _F("O3", "integer", "Owner 3", False, _N, "", 0, None),
        _F("F3", "number", "Fraction by owner 3", False, _N, "", 0.0, (0.0, 1.0)),
        _F("O4", "integer", "Owner 4", False, _N, "", 0, None),
        _F("F4", "number", "Fraction by owner 4", False, _N, "", 0.0, (0.0, 1.0)),
        _F("VECGRP", "string", "Vector group (12 chars)", False, _N, "", _BLANK12, None),
        # Line 2 -- impedance
        _F("R1_2", "number", "R winding 1-2 (CZ dep)", True, _M, "pu", 0.0, None),
        _F("X1_2", "number", "X winding 1-2 (CZ dep)", True, _M, "pu", None, None),
        _F("SBASE1_2", "number", "MVA base winding 1-2", True, _N, "MVA", 100.0, None),
        _F("R2_3", "number", "R winding 2-3 (3W only)", False, _M, "pu", 0.0, None),
        _F("X2_3", "number", "X winding 2-3 (3W only)", False, _M, "pu", 0.0, None),
        _F("SBASE2_3", "number", "MVA base winding 2-3", False, _N, "MVA", 100.0, None),
        _F("R3_1", "number", "R winding 3-1 (3W only)", False, _M, "pu", 0.0, None),
        _F("X3_1", "number", "X winding 3-1 (3W only)", False, _M, "pu", 0.0, None),
        _F("SBASE3_1", "number", "MVA base winding 3-1", False, _N, "MVA", 100.0, None),
        _F("VMSTAR", "number", "Star bus voltage mag", False, _B, "pu", 1.0, None),
        _F("ANSTAR", "number", "Star bus voltage angle", False, _N, "deg", 0.0, None),
        # Line 3 -- winding 1
        _F("WINDV1", "number", "Winding 1 turns ratio", True, _M, "", 1.0, None, False, P),
        _F("NOMV1", "number", "Winding 1 nominal kV", True, _N, "kV", 0.0, None, False, P),
        _F("ANG1", "number", "Winding 1 phase shift", True, _N, "deg", 0.0, None, False, P),
        _F("RATA1", "number", "Winding 1 rating A", True, _N, "MVA", 0.0, None, False, P),
        _F("RATB1", "number", "Winding 1 rating B", False, _N, "MVA", 0.0, None),
        _F("RATC1", "number", "Winding 1 rating C", False, _N, "MVA", 0.0, None),
        _F("COD1", "integer", "Winding 1 tap control", False, _N, "", 0, None),
        _F("CONT1", "integer", "Winding 1 ctrl bus", False, _N, "", 0, None),
        _F("RMA1", "number", "Winding 1 upper tap limit", False, _M, "", 1.1, None),
        _F("RMI1", "number", "Winding 1 lower tap limit", False, _M, "", 0.9, None),
        _F("VMA1", "number", "Winding 1 upper V limit", False, _M, "", 1.1, None),
        _F("VMI1", "number", "Winding 1 lower V limit", False, _M, "", 0.9, None),
        _F("NTP1", "integer", "Winding 1 tap positions", False, _N, "", 33, None),
        _F("TAB1", "integer", "Winding 1 impcor table", False, _N, "", 0, None),
        _F("CR1", "number", "Winding 1 LDC resistance", False, _S, "pu", 0.0, None),
        _F("CX1", "number", "Winding 1 LDC reactance", False, _S, "pu", 0.0, None),
        _F("CNXA1", "integer", "Winding 1 conn angle", False, _N, "", 0, None),
        # Line 4 -- winding 2
        _F("WINDV2", "number", "Winding 2 turns ratio", True, _M, "", 1.0, None, False, P),
        _F("NOMV2", "number", "Winding 2 nominal kV", True, _N, "kV", 0.0, None, False, P),
        _F("ANG2", "number", "Winding 2 phase shift", False, _N, "deg", 0.0, None),
        _F("RATA2", "number", "Winding 2 rating A", False, _N, "MVA", 0.0, None, False, P),
        _F("RATB2", "number", "Winding 2 rating B", False, _N, "MVA", 0.0, None),
        _F("RATC2", "number", "Winding 2 rating C", False, _N, "MVA", 0.0, None),
        _F("COD2", "integer", "Winding 2 tap control", False, _N, "", 0, None),
        _F("CONT2", "integer", "Winding 2 ctrl bus", False, _N, "", 0, None),
        _F("RMA2", "number", "Winding 2 upper tap limit", False, _M, "", 1.1, None),
        _F("RMI2", "number", "Winding 2 lower tap limit", False, _M, "", 0.9, None),
        _F("VMA2", "number", "Winding 2 upper V limit", False, _M, "", 1.1, None),
        _F("VMI2", "number", "Winding 2 lower V limit", False, _M, "", 0.9, None),
        _F("NTP2", "integer", "Winding 2 tap positions", False, _N, "", 33, None),
        _F("TAB2", "integer", "Winding 2 impcor table", False, _N, "", 0, None),
        _F("CR2", "number", "Winding 2 LDC resistance", False, _S, "pu", 0.0, None),
        _F("CX2", "number", "Winding 2 LDC reactance", False, _S, "pu", 0.0, None),
        _F("CNXA2", "integer", "Winding 2 conn angle", False, _N, "", 0, None),
        # Line 5 -- winding 3 (nullable for 2W)
        _F("WINDV3", "number", "Winding 3 turns ratio", False, _M, "", 1.0, None, False, P),
        _F("NOMV3", "number", "Winding 3 nominal kV", False, _N, "kV", 0.0, None, False, P),
        _F("ANG3", "number", "Winding 3 phase shift", False, _N, "deg", 0.0, None),
        _F("RATA3", "number", "Winding 3 rating A", False, _N, "MVA", 0.0, None, False, P),
        _F("RATB3", "number", "Winding 3 rating B", False, _N, "MVA", 0.0, None),
        _F("RATC3", "number", "Winding 3 rating C", False, _N, "MVA", 0.0, None),
        _F("COD3", "integer", "Winding 3 tap control", False, _N, "", 0, None),
        _F("CONT3", "integer", "Winding 3 ctrl bus", False, _N, "", 0, None),
        _F("RMA3", "number", "Winding 3 upper tap limit", False, _M, "", 1.1, None),
        _F("RMI3", "number", "Winding 3 lower tap limit", False, _M, "", 0.9, None),
        _F("VMA3", "number", "Winding 3 upper V limit", False, _M, "", 1.1, None),
        _F("VMI3", "number", "Winding 3 lower V limit", False, _M, "", 0.9, None),
        _F("NTP3", "integer", "Winding 3 tap positions", False, _N, "", 33, None),
        _F("TAB3", "integer", "Winding 3 impcor table", False, _N, "", 0, None),
        _F("CR3", "number", "Winding 3 LDC resistance", False, _S, "pu", 0.0, None),
        _F("CX3", "number", "Winding 3 LDC reactance", False, _S, "pu", 0.0, None),
        _F("CNXA3", "integer", "Winding 3 conn angle", False, _N, "", 0, None),
    ]


def _area_fields() -> list[FieldSpec]:
    P = True  # noqa: N806
    return [
        _F("I", "integer", "Area number", True, _N, "", None, None),
        _F("ISW", "integer", "Area slack bus number", True, _N, "", 0, None, False, P),
        _F("PDES", "number", "Desired net interchange", True, _N, "MW", 0.0, None, False, P),
        _F("PTOL", "number", "Interchange tolerance", True, _N, "MW", 10.0, None, False, P),
        _F("ARNAME", "string", "Area name (12 chars)", True, _N, "", _BLANK12, None),
    ]


def _two_terminal_dc_fields() -> list[FieldSpec]:
    return [
        _F("NAME", "string", "DC line name", True, _N, "", None, None),
        _F("MDC", "integer", "Control mode (0-2)", True, _N, "", 0, (0, 2)),
        _F("RDC", "number", "DC line resistance", True, _N, "ohm", None, None),
        _F("SETVL", "number", "Current or power demand", True, _N, "", 0.0, None),
        _F("VSCHD", "number", "Scheduled DC voltage", True, _N, "kV", 0.0, None),
        _F("VCMOD", "number", "Mode switch DC voltage", False, _N, "", 0.0, None),
        _F("RCOMP", "number", "Compounding resistance", False, _N, "", 0.0, None),
        _F("DELTI", "number", "Inverter firing angle margin", False, _N, "deg", 0.0, None),
        _F("METER", "string", "Metered end (R or I)", False, _N, "", "I", None),
        _F("DCVMIN", "number", "Min DC voltage", False, _N, "pu", 0.0, None),
        _F("CCCITMX", "integer", "Max converter ctrl iters", False, _N, "", 20, None),
        _F("CCCACC", "number", "Converter ctrl accel factor", False, _N, "", 1.0, None),
        # Rectifier
        _F("IPR", "integer", "Rectifier bus", True, _N, "", None, None),
        _F("NBR", "integer", "Rectifier bridges", True, _N, "", None, None),
        _F("ANMXR", "number", "Max rect firing angle", False, _N, "deg", 0.0, None),
        _F("ANMNR", "number", "Min rect firing angle", False, _N, "deg", 0.0, None),
        _F("RCR", "number", "Rect commutating R", False, _N, "", 0.0, None),
        _F("XCR", "number", "Rect commutating X", False, _N, "", 0.0, None),
        _F("EBASR", "number", "Rect primary base kV", False, _N, "kV", 0.0, None),
        _F("TRR", "number", "Rect xfmr ratio", False, _N, "", 1.0, None),
        _F("TAPR", "number", "Rect tap setting", False, _N, "", 1.0, None),
        _F("TMXR", "number", "Max rect tap", False, _N, "", 1.5, None),
        _F("TMNR", "number", "Min rect tap", False, _N, "", 0.51, None),
        _F("STPR", "number", "Rect tap step", False, _N, "", 0.00625, None),
        _F("ICR", "integer", "Rect firing angle ctrl bus", False, _N, "", 0, None),
        _F("IFR", "integer", "Rect commutating bus (from)", False, _N, "", 0, None),
        _F("ITR", "integer", "Rect commutating bus (to)", False, _N, "", 0, None),
        _F("IDR", "string", "Rect circuit ID", False, _N, "", "1 ", None),
        _F("XCAPR", "number", "Rect capacitor reactance", False, _N, "", 0.0, None),
        # Inverter
        _F("IPI", "integer", "Inverter bus", True, _N, "", None, None),
        _F("NBI", "integer", "Inverter bridges", True, _N, "", None, None),
        _F("ANMXI", "number", "Max inv firing angle", False, _N, "deg", 0.0, None),
        _F("ANMNI", "number", "Min inv firing angle", False, _N, "deg", 0.0, None),
        _F("RCI", "number", "Inv commutating R", False, _N, "", 0.0, None),
        _F("XCI", "number", "Inv commutating X", False, _N, "", 0.0, None),
        _F("EBASI", "number", "Inv primary base kV", False, _N, "kV", 0.0, None),
        _F("TRI", "number", "Inv xfmr ratio", False, _N, "", 1.0, None),
        _F("TAPI", "number", "Inv tap setting", False, _N, "", 1.0, None),
        _F("TMXI", "number", "Max inv tap", False, _N, "", 1.5, None),
        _F("TMNI", "number", "Min inv tap", False, _N, "", 0.51, None),
        _F("STPI", "number", "Inv tap step", False, _N, "", 0.00625, None),
        _F("ICI", "integer", "Inv firing angle ctrl bus", False, _N, "", 0, None),
        _F("IFI", "integer", "Inv commutating bus (from)", False, _N, "", 0, None),
        _F("ITI", "integer", "Inv commutating bus (to)", False, _N, "", 0, None),
        _F("IDI", "string", "Inv circuit ID", False, _N, "", "1 ", None),
        _F("XCAPI", "number", "Inv capacitor reactance", False, _N, "", 0.0, None),
    ]


def _vsc_dc_fields() -> list[FieldSpec]:
    return [
        _F("NAME", "string", "VSC DC line name", True, _N, "", None, None),
        _F("MDC", "integer", "Control mode", True, _N, "", 0, None),
        _F("RDC", "number", "DC line resistance", True, _N, "ohm", None, None),
        _F("O1", "integer", "Owner 1", False, _N, "", 1, None),
        _F("F1", "number", "Fraction by owner 1", False, _N, "", 1.0, None),
        _F("O2", "integer", "Owner 2", False, _N, "", 0, None),
        _F("F2", "number", "Fraction by owner 2", False, _N, "", 0.0, None),
        _F("O3", "integer", "Owner 3", False, _N, "", 0, None),
        _F("F3", "number", "Fraction by owner 3", False, _N, "", 0.0, None),
        _F("O4", "integer", "Owner 4", False, _N, "", 0, None),
        _F("F4", "number", "Fraction by owner 4", False, _N, "", 0.0, None),
        # Converter 1
        _F("IBUS1", "integer", "Converter 1 AC bus", True, _N, "", None, None),
        _F("TYPE1", "integer", "Converter 1 type", False, _N, "", 1, None),
        _F("MODE1", "integer", "Converter 1 mode", False, _N, "", 1, None),
        _F("DCSET1", "number", "Converter 1 DC setpoint", False, _N, "", 0.0, None),
        _F("ACSET1", "number", "Converter 1 AC setpoint", False, _N, "", 1.0, None),
        _F("ALOSS1", "number", "Converter 1 loss A", False, _N, "", 0.0, None),
        _F("BLOSS1", "number", "Converter 1 loss B", False, _N, "", 0.0, None),
        _F("MINLOSS1", "number", "Converter 1 min loss", False, _N, "", 0.0, None),
        _F("SMAX1", "number", "Converter 1 MVA rating", False, _N, "MVA", 0.0, None),
        _F("IMAX1", "number", "Converter 1 current rating", False, _N, "A", 0.0, None),
        _F("PWF1", "number", "Converter 1 power weight", False, _N, "", 1.0, None),
        _F("MAXQ1", "number", "Converter 1 max Q", False, _N, "MVAR", 9999.0, None),
        _F("MINQ1", "number", "Converter 1 min Q", False, _N, "MVAR", -9999.0, None),
        _F("REMOT1", "integer", "Converter 1 remote bus", False, _N, "", 0, None),
        _F("RMPCT1", "number", "Converter 1 MVAR pct", False, _N, "%", 100.0, None),
        # Converter 2
        _F("IBUS2", "integer", "Converter 2 AC bus", True, _N, "", None, None),
        _F("TYPE2", "integer", "Converter 2 type", False, _N, "", 1, None),
        _F("MODE2", "integer", "Converter 2 mode", False, _N, "", 1, None),
        _F("DCSET2", "number", "Converter 2 DC setpoint", False, _N, "", 0.0, None),
        _F("ACSET2", "number", "Converter 2 AC setpoint", False, _N, "", 1.0, None),
        _F("ALOSS2", "number", "Converter 2 loss A", False, _N, "", 0.0, None),
        _F("BLOSS2", "number", "Converter 2 loss B", False, _N, "", 0.0, None),
        _F("MINLOSS2", "number", "Converter 2 min loss", False, _N, "", 0.0, None),
        _F("SMAX2", "number", "Converter 2 MVA rating", False, _N, "MVA", 0.0, None),
        _F("IMAX2", "number", "Converter 2 current rating", False, _N, "A", 0.0, None),
        _F("PWF2", "number", "Converter 2 power weight", False, _N, "", 1.0, None),
        _F("MAXQ2", "number", "Converter 2 max Q", False, _N, "MVAR", 9999.0, None),
        _F("MINQ2", "number", "Converter 2 min Q", False, _N, "MVAR", -9999.0, None),
        _F("REMOT2", "integer", "Converter 2 remote bus", False, _N, "", 0, None),
        _F("RMPCT2", "number", "Converter 2 MVAR pct", False, _N, "%", 100.0, None),
    ]


def _impedance_correction_fields() -> list[FieldSpec]:
    fields: list[FieldSpec] = [
        _F("T", "integer", "Correction table number", True, _N, "", None, None),
    ]
    for i in range(1, 12):
        fields.append(_F(f"T{i}", "number", f"Tap ratio/angle pair {i}", False, _N, "", 0.0, None))
        fields.append(
            _F(f"F{i}", "number", f"Correction factor pair {i}", False, _N, "", 0.0, None)
        )
    return fields


def _multi_terminal_dc_fields() -> list[FieldSpec]:
    return [
        _F("NAME", "string", "MT DC line name", True, _N, "", None, None),
        _F("NCONV", "integer", "Number of AC converters", True, _N, "", 0, None),
        _F("NDCBS", "integer", "Number of DC buses", True, _N, "", 0, None),
        _F("NDCLN", "integer", "Number of DC links", True, _N, "", 0, None),
        _F("MDC", "integer", "Control mode", False, _N, "", 0, None),
        _F("VCONV", "integer", "DC voltage ctrl converter", False, _N, "", 0, None),
        _F("VCMOD", "number", "Mode switch DC voltage", False, _N, "", 0.0, None),
        _F("VCONVN", "integer", "New voltage ctrl converter", False, _N, "", 0, None),
    ]


def _multi_section_line_fields() -> list[FieldSpec]:
    P = True  # noqa: N806
    fields: list[FieldSpec] = [
        _F("I", "integer", "From bus number", True, _N, "", None, None, False, P),
        _F("J", "integer", "To bus number", True, _N, "", None, None, False, P),
        _F("ID", "string", "Line identifier", True, _N, "", "1 ", None, False, P),
        _F("MET", "integer", "Metered end flag", False, _N, "", 1, (1, 2)),
    ]
    for i in range(1, 10):
        fields.append(
            _F(f"DUM{i}", "integer", f"Intermediate bus {i}", True, _N, "", 0, None, False, P)
        )
    return fields


def _zone_fields() -> list[FieldSpec]:
    return [
        _F("I", "integer", "Zone number", True, _N, "", None, None),
        _F("ZONAME", "string", "Zone name (12 chars)", True, _N, "", _BLANK12, None),
    ]


def _interarea_transfer_fields() -> list[FieldSpec]:
    return [
        _F("ARFROM", "integer", "From area number", True, _N, "", None, None),
        _F("ARTO", "integer", "To area number", True, _N, "", None, None),
        _F("TRID", "string", "Transfer ID (2 chars)", True, _N, "", "1 ", None),
        _F("PTRAN", "number", "Transfer amount", True, _N, "MW", 0.0, None),
    ]


def _owner_fields() -> list[FieldSpec]:
    return [
        _F("I", "integer", "Owner number", True, _N, "", None, None),
        _F("OWNAME", "string", "Owner name (12 chars)", True, _N, "", _BLANK12, None),
    ]


def _facts_fields() -> list[FieldSpec]:
    return [
        _F("NAME", "string", "FACTS device name", True, _N, "", None, None),
        _F("I", "integer", "Sending end bus", True, _N, "", None, None),
        _F("J", "integer", "Terminal bus (0=shunt)", True, _N, "", 0, None),
        _F("MODE", "integer", "FACTS control mode", True, _N, "", 1, None),
        _F("SET1", "number", "Control setpoint 1", False, _N, "", 0.0, None),
        _F("SET2", "number", "Control setpoint 2", False, _N, "", 0.0, None),
        _F("VSREF", "number", "Series voltage reference", False, _B, "pu", 1.0, None),
        _F("REMOT", "integer", "Remote bus for V control", False, _N, "", 0, None),
        _F("MESSION", "number", "Sending end impedance", False, _N, "", 0.0, None),
        _F("LINX", "number", "Series reactance", False, _S, "pu", 0.05, None),
        _F("RMPCT", "number", "MVAR pct for remote reg", False, _N, "%", 100.0, None),
        _F("OWNER", "integer", "Owner number", False, _N, "", 1, None),
        _F("SET3", "number", "Control setpoint 3", False, _N, "", 0.0, None),
        _F("SET4", "number", "Control setpoint 4", False, _N, "", 0.0, None),
    ]


def _switched_shunt_fields() -> list[FieldSpec]:
    P = True  # noqa: N806
    fields: list[FieldSpec] = [
        _F("I", "integer", "Bus number", True, _N, "", None, None),
        _F("MODSW", "integer", "Control mode (0-2)", True, _N, "", 1, (0, 2), False, P),
        _F("ADJM", "integer", "Adj method (0-1)", False, _N, "", 0, (0, 1)),
        _F("STAT", "integer", "Status (1=in, 0=out)", True, _N, "", 1, (0, 1)),
        _F("VSWHI", "number", "Ctrl voltage upper limit", True, _B, "pu", 1.0, None),
        _F("VSWLO", "number", "Ctrl voltage lower limit", True, _B, "pu", 1.0, None),
        _F("SWREM", "integer", "Remote bus (0=local)", True, _N, "", 0, None, False, P),
        _F("RMPCT", "number", "MVAR pct for remote reg", False, _N, "%", 100.0, None),
        _F("RMIDNT", "string", "Shunt name", False, _N, "", "", None),
        _F("BINIT", "number", "Initial susceptance", True, _N, "MVAR", 0.0, None, False, P),
    ]
    for i in range(1, 9):
        fields.append(
            _F(f"N{i}", "integer", f"Steps in block {i}", True, _N, "", 0, None, False, P)
        )
        fields.append(
            _F(
                f"B{i}",
                "number",
                f"Susceptance/step blk {i}",
                True,
                _N,
                "MVAR",
                0.0,
                None,
                False,
                P,
            )
        )
    return fields


# ---------------------------------------------------------------------------
# Table name derivation
# ---------------------------------------------------------------------------


def _record_type_to_table_name(record_type: str) -> str:
    """Convert PSS/E record type name to table file name stem.

    Args:
        record_type: PSS/E v31 record type name.

    Returns:
        Lowercase, underscore-separated table name.
    """
    return record_type.lower().replace(" ", "_").replace("-", "_")


# ---------------------------------------------------------------------------
# Schema generation
# ---------------------------------------------------------------------------

_TABLE_FIELD_BUILDERS: dict[str, Callable[[], list[FieldSpec]]] = {
    "Bus": _bus_fields,
    "Load": _load_fields,
    "Fixed Shunt": _fixed_shunt_fields,
    "Generator": _generator_fields,
    "Branch": _branch_fields,
    "Transformer": _transformer_fields,
    "Area": _area_fields,
    "Two-Terminal DC": _two_terminal_dc_fields,
    "VSC DC": _vsc_dc_fields,
    "Impedance Correction": _impedance_correction_fields,
    "Multi-Terminal DC": _multi_terminal_dc_fields,
    "Multi-Section Line": _multi_section_line_fields,
    "Zone": _zone_fields,
    "Interarea Transfer": _interarea_transfer_fields,
    "Owner": _owner_fields,
    "FACTS": _facts_fields,
    "Switched Shunt": _switched_shunt_fields,
}

_TABLE_PRIMARY_KEYS: dict[str, list[str]] = {
    "Bus": ["I"],
    "Load": ["I", "ID"],
    "Fixed Shunt": ["I", "ID"],
    "Generator": ["I", "ID"],
    "Branch": ["I", "J", "CKT"],
    "Transformer": ["I", "J", "K", "CKT"],
    "Area": ["I"],
    "Two-Terminal DC": ["NAME"],
    "VSC DC": ["NAME"],
    "Impedance Correction": ["T"],
    "Multi-Terminal DC": ["NAME"],
    "Multi-Section Line": ["I", "J", "ID"],
    "Zone": ["I"],
    "Interarea Transfer": ["ARFROM", "ARTO", "TRID"],
    "Owner": ["I"],
    "FACTS": ["NAME"],
    "Switched Shunt": ["I"],
}

_TABLE_DESCRIPTIONS: dict[str, str] = {
    "Bus": ("PSS/E v31 Bus record type. Each row represents one bus in the network model."),
    "Load": ("PSS/E v31 Load record type. Each row represents one load at a bus."),
    "Fixed Shunt": (
        "PSS/E v31 Fixed Shunt record type. Each row represents a fixed shunt element."
    ),
    "Generator": ("PSS/E v31 Generator record type. Each row represents one generating unit."),
    "Branch": ("PSS/E v31 Branch record type. Each row represents a transmission line or cable."),
    "Transformer": (
        "PSS/E v31 Transformer record type. Multi-line records "
        "flattened into one row. 2-winding (K=0) and 3-winding "
        "(K!=0) share the same schema."
    ),
    "Area": ("PSS/E v31 Area record type. Each row defines an area for interchange control."),
    "Two-Terminal DC": ("PSS/E v31 Two-Terminal DC line record type."),
    "VSC DC": "PSS/E v31 VSC DC line record type.",
    "Impedance Correction": ("PSS/E v31 Impedance Correction table record type."),
    "Multi-Terminal DC": ("PSS/E v31 Multi-Terminal DC line header record type."),
    "Multi-Section Line": (
        "PSS/E v31 Multi-Section Line grouping record type. DUM fields define intermediate buses."
    ),
    "Zone": "PSS/E v31 Zone record type.",
    "Interarea Transfer": ("PSS/E v31 Interarea Transfer record type."),
    "Owner": "PSS/E v31 Owner record type.",
    "FACTS": "PSS/E v31 FACTS device record type.",
    "Switched Shunt": (
        "PSS/E v31 Switched Shunt record type. N1-N8 and "
        "B1-B8 define discrete switching step blocks."
    ),
}

_MULTI_LINE_TYPES = {"Transformer", "Multi-Terminal DC"}


def get_table_schemas() -> list[TableSchema]:
    """Return table schemas for all 17 PSS/E v31 record types.

    This is the master field inventory. Only tables whose record type
    appears in the non-empty sections list (from D3) will get JSON
    Schema files written.

    Returns:
        List of TableSchema in PSS/E v31 section order.
    """
    schemas: list[TableSchema] = []
    for rt in PSSE_V31_RECORD_TYPES:
        builder = _TABLE_FIELD_BUILDERS[rt]
        schemas.append(
            TableSchema(
                record_type=rt,
                table_name=_record_type_to_table_name(rt),
                description=_TABLE_DESCRIPTIONS[rt],
                fields=builder(),
                primary_key=_TABLE_PRIMARY_KEYS[rt],
                multi_line_record=rt in _MULTI_LINE_TYPES,
            )
        )
    return schemas


def table_schema_to_json_schema(table: TableSchema) -> dict:
    """Convert a TableSchema to a JSON Schema Draft 2020-12 document.

    Args:
        table: The table schema to convert.

    Returns:
        A dict that is a valid JSON Schema Draft 2020-12 document.
    """
    properties: dict[str, dict] = {}
    required_fields: list[str] = []

    for f in table.fields:
        prop: dict = {
            "type": f.data_type,
            "description": f.description,
            "x-psse-unit": f.unit,
            "x-psse-per-unit-base": f.per_unit_base.value,
            "x-psse-default": f.default_value,
            "x-psse-preservation-critical": f.preservation_critical,
            "x-psse-present-but-inactive": f.present_but_inactive,
        }
        if f.valid_range is not None:
            prop["x-psse-valid-range"] = list(f.valid_range)
        else:
            prop["x-psse-valid-range"] = None

        properties[f.name] = prop
        if f.required:
            required_fields.append(f.name)

    return {
        "$schema": ("https://json-schema.org/draft/2020-12/schema"),
        "$id": f"schemas/{table.table_name}.schema.json",
        "title": table.record_type,
        "description": table.description,
        "type": "object",
        "properties": properties,
        "required": required_fields,
        "additionalProperties": False,
    }


def manifest_to_json_schema() -> dict:
    """Return the JSON Schema for the intermediate format manifest.

    Returns:
        A dict that is a valid JSON Schema Draft 2020-12 document.
    """
    return {
        "$schema": ("https://json-schema.org/draft/2020-12/schema"),
        "$id": "schemas/manifest.schema.json",
        "title": "Intermediate Format Manifest",
        "description": (
            "Top-level manifest listing all tables in the intermediate format with metadata."
        ),
        "type": "object",
        "properties": {
            "sbase": {
                "type": "number",
                "description": "System MVA base",
            },
            "basfrq": {
                "type": "number",
                "description": "System base frequency (Hz)",
            },
            "rev": {
                "type": "number",
                "description": "PSS/E revision number",
            },
            "case_id": {
                "type": "string",
                "description": "Case identification string",
            },
            "canonical_parser": {
                "type": "string",
                "enum": ["matpower", "gridcal"],
                "description": "Canonical parser from D6",
            },
            "tables": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "table_name": {"type": "string"},
                        "record_type": {"type": "string"},
                        "file_name": {"type": "string"},
                        "record_count": {
                            "type": "integer",
                            "minimum": 0,
                        },
                        "column_count": {
                            "type": "integer",
                            "minimum": 1,
                        },
                        "schema_file": {"type": "string"},
                    },
                    "required": [
                        "table_name",
                        "record_type",
                        "file_name",
                        "record_count",
                        "column_count",
                        "schema_file",
                    ],
                },
            },
            "total_records": {
                "type": "integer",
                "minimum": 0,
            },
            "total_tables": {
                "type": "integer",
                "minimum": 1,
            },
            "non_empty_record_types": {
                "type": "array",
                "items": {"type": "string"},
            },
            "schema_version": {"type": "string"},
            "generated_timestamp": {
                "type": "string",
                "format": "date-time",
            },
        },
        "required": [
            "sbase",
            "basfrq",
            "rev",
            "case_id",
            "canonical_parser",
            "tables",
            "total_records",
            "total_tables",
            "non_empty_record_types",
            "schema_version",
            "generated_timestamp",
        ],
        "additionalProperties": False,
    }


# ---------------------------------------------------------------------------
# Schema I/O
# ---------------------------------------------------------------------------


def write_schemas(
    output_dir: Path,
    non_empty_types: list[str],
    present_but_inactive: dict[str, list[str]] | None = None,
) -> list[Path]:
    """Write JSON Schema files for non-empty record types + manifest.

    Args:
        output_dir: Root directory for schema output.
        non_empty_types: PSS/E record type names with non-zero count.
        present_but_inactive: Optional dict mapping record type to
            list of field names uniformly at default values.

    Returns:
        List of paths to written schema files.

    Raises:
        ValueError: If a record type is not recognized.
    """
    all_schemas = {ts.record_type: ts for ts in get_table_schemas()}

    for rt in non_empty_types:
        if rt not in all_schemas:
            msg = f"Unknown record type: {rt!r}"
            raise ValueError(msg)

    schema_dir = output_dir / "schemas"
    schema_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []

    for rt in non_empty_types:
        ts = all_schemas[rt]

        # Apply present_but_inactive annotations
        if present_but_inactive and rt in present_but_inactive:
            inactive_names = set(present_but_inactive[rt])
            updated = []
            for f in ts.fields:
                if f.name in inactive_names:
                    updated.append(
                        FieldSpec(
                            name=f.name,
                            data_type=f.data_type,
                            description=f.description,
                            required=f.required,
                            per_unit_base=f.per_unit_base,
                            unit=f.unit,
                            default_value=f.default_value,
                            valid_range=f.valid_range,
                            present_but_inactive=True,
                            preservation_critical=(f.preservation_critical),
                        )
                    )
                else:
                    updated.append(f)
            ts = TableSchema(
                record_type=ts.record_type,
                table_name=ts.table_name,
                description=ts.description,
                fields=updated,
                primary_key=ts.primary_key,
                multi_line_record=ts.multi_line_record,
                notes=ts.notes,
            )

        schema_dict = table_schema_to_json_schema(ts)
        path = schema_dir / f"{ts.table_name}.schema.json"
        path.write_text(
            json.dumps(schema_dict, indent=2) + "\n",
            encoding="utf-8",
        )
        written.append(path)

    # Write manifest schema
    manifest_schema = manifest_to_json_schema()
    manifest_path = schema_dir / "manifest.schema.json"
    manifest_path.write_text(
        json.dumps(manifest_schema, indent=2) + "\n",
        encoding="utf-8",
    )
    written.append(manifest_path)

    return written


def load_schema(schema_path: Path) -> dict:
    """Load a JSON Schema file and return the parsed dict.

    Args:
        schema_path: Path to a .schema.json file.

    Returns:
        The parsed JSON Schema dict.

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")
    return json.loads(schema_path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# present-but-inactive detection
# ---------------------------------------------------------------------------


def detect_inactive_fields(
    csv_dir: Path,
    non_empty_types: list[str],
    record_type_to_table_name: dict[str, str],
) -> dict[str, list[str]]:
    """Scan CSV exports to find fields uniformly at default values.

    Args:
        csv_dir: Directory containing canonical parser CSV exports.
        non_empty_types: PSS/E record type names to check.
        record_type_to_table_name: Mapping from PSS/E record type
            name to the CSV file stem.

    Returns:
        Dict mapping record type name to list of inactive fields.
    """
    all_schemas = {ts.record_type: ts for ts in get_table_schemas()}
    result: dict[str, list[str]] = {}

    for rt in non_empty_types:
        if rt not in all_schemas:
            continue
        ts = all_schemas[rt]
        csv_stem = record_type_to_table_name.get(rt)
        if csv_stem is None:
            continue

        csv_path = csv_dir / f"{csv_stem}.csv"
        if not csv_path.exists():
            continue

        try:
            with open(csv_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        except (OSError, csv.Error):
            continue

        if not rows:
            continue

        # Build field-name -> default mapping
        field_defaults: dict[str, int | float | str | None] = {}
        for fs in ts.fields:
            if fs.default_value is not None:
                field_defaults[fs.name] = fs.default_value

        inactive: list[str] = []
        for fname, default_val in field_defaults.items():
            if fname not in rows[0]:
                continue

            all_default = True
            for row in rows:
                val = row.get(fname, "")
                try:
                    if isinstance(default_val, int):
                        if int(float(val)) != default_val:
                            all_default = False
                            break
                    elif isinstance(default_val, float):
                        if abs(float(val) - default_val) > 1e-10:
                            all_default = False
                            break
                    else:
                        if str(val).strip() != str(default_val).strip():
                            all_default = False
                            break
                except (ValueError, TypeError):
                    all_default = False
                    break

            if all_default:
                inactive.append(fname)

        if inactive:
            result[rt] = sorted(inactive)

    return result


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_tables(
    csv_dir: Path,
    schema_dir: Path,
    manifest_path: Path,
) -> ConformanceReport:
    """Validate intermediate format CSV tables against the schema.

    Args:
        csv_dir: Directory containing CSV tables.
        schema_dir: Directory containing JSON Schema files.
        manifest_path: Path to the manifest JSON.

    Returns:
        A ConformanceReport summarizing all findings.
    """
    errors: list[ConformanceFinding] = []
    warnings: list[ConformanceFinding] = []
    info: list[ConformanceFinding] = []
    manifest_valid = True

    # 1. Load manifest
    try:
        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as e:
        errors.append(
            ConformanceFinding(
                "__manifest__",
                "",
                ConformanceLevel.ERROR,
                f"Cannot load manifest: {e}",
                "manifest_load_error",
            )
        )
        return ConformanceReport(
            tables_checked=0,
            tables_expected=0,
            errors=errors,
            warnings=warnings,
            info=info,
            is_conformant=False,
            manifest_valid=False,
        )

    # Check manifest against its schema
    manifest_schema_path = schema_dir / "manifest.schema.json"
    if manifest_schema_path.exists():
        try:
            ms = load_schema(manifest_schema_path)
            _validate_against_schema(manifest_data, ms)
        except Exception as e:
            manifest_valid = False
            errors.append(
                ConformanceFinding(
                    "__manifest__",
                    "",
                    ConformanceLevel.ERROR,
                    f"Manifest schema validation failed: {e}",
                    "manifest_schema_invalid",
                )
            )

    tables_list = manifest_data.get("tables", [])
    tables_expected = len(tables_list)
    tables_checked = 0

    all_schemas = {ts.table_name: ts for ts in get_table_schemas()}

    for table_entry in tables_list:
        tname = table_entry.get("table_name", "")
        fname = table_entry.get("file_name", "")
        expected_count = table_entry.get("record_count", 0)

        # 2. Table presence
        csv_path = csv_dir / fname
        if not csv_path.exists():
            errors.append(
                ConformanceFinding(
                    tname,
                    "",
                    ConformanceLevel.ERROR,
                    f"CSV file not found: {fname}",
                    "missing_table",
                )
            )
            continue

        tables_checked += 1

        # Load schema
        spath = schema_dir / f"{tname}.schema.json"
        if not spath.exists():
            warnings.append(
                ConformanceFinding(
                    tname,
                    "",
                    ConformanceLevel.WARNING,
                    f"No schema: {tname}.schema.json",
                    "missing_schema",
                )
            )
            continue

        schema = load_schema(spath)
        required_fields = schema.get("required", [])
        schema_props = schema.get("properties", {})

        # Read CSV
        try:
            with open(csv_path, encoding="utf-8") as fh:
                reader = csv.DictReader(fh)
                csv_headers = reader.fieldnames or []
                rows = list(reader)
        except (OSError, csv.Error) as e:
            errors.append(
                ConformanceFinding(
                    tname,
                    "",
                    ConformanceLevel.ERROR,
                    f"Cannot read CSV: {e}",
                    "csv_read_error",
                )
            )
            continue

        # 3. Required fields
        hdr_set = set(csv_headers)
        for rf in required_fields:
            if rf not in hdr_set:
                errors.append(
                    ConformanceFinding(
                        tname,
                        rf,
                        ConformanceLevel.ERROR,
                        f"Required field '{rf}' missing",
                        "missing_required_field",
                    )
                )

        # 4. Extra columns
        schema_set = set(schema_props.keys())
        for col in csv_headers:
            if col not in schema_set:
                info.append(
                    ConformanceFinding(
                        tname,
                        col,
                        ConformanceLevel.INFO,
                        f"Extra column '{col}'",
                        "extra_column",
                    )
                )

        # 5. Type spot-check (first 100 rows)
        check_rows = rows[:100]
        for cname, cschema in schema_props.items():
            if cname not in hdr_set:
                continue
            ctype = cschema.get("type", "string")
            for ridx, row in enumerate(check_rows):
                val = row.get(cname, "")
                if val == "" or val is None:
                    continue
                if ctype == "integer":
                    try:
                        int(float(val))
                    except (ValueError, TypeError):
                        warnings.append(
                            ConformanceFinding(
                                tname,
                                cname,
                                ConformanceLevel.WARNING,
                                f"Row {ridx}: '{val}' not int",
                                "type_mismatch",
                            )
                        )
                        break
                elif ctype == "number":
                    try:
                        float(val)
                    except (ValueError, TypeError):
                        warnings.append(
                            ConformanceFinding(
                                tname,
                                cname,
                                ConformanceLevel.WARNING,
                                f"Row {ridx}: '{val}' not num",
                                "type_mismatch",
                            )
                        )
                        break

        # 6. Record count check
        actual = len(rows)
        if actual != expected_count:
            info.append(
                ConformanceFinding(
                    tname,
                    "",
                    ConformanceLevel.INFO,
                    (f"Count: manifest={expected_count}, CSV={actual}"),
                    "record_count_mismatch",
                )
            )

        # 7. Preservation-critical fields
        ts = all_schemas.get(tname)
        if ts:
            for fs in ts.fields:
                if not fs.preservation_critical:
                    continue
                if fs.name not in hdr_set:
                    errors.append(
                        ConformanceFinding(
                            tname,
                            fs.name,
                            ConformanceLevel.ERROR,
                            (f"Preservation-critical '{fs.name}' missing"),
                            "missing_preservation_critical",
                        )
                    )
                elif rows:
                    all_null = all(row.get(fs.name, "") in ("", None) for row in rows)
                    if all_null:
                        warnings.append(
                            ConformanceFinding(
                                tname,
                                fs.name,
                                ConformanceLevel.WARNING,
                                (f"'{fs.name}' null in all records"),
                                "preservation_critical_all_null",
                            )
                        )

    return ConformanceReport(
        tables_checked=tables_checked,
        tables_expected=tables_expected,
        errors=errors,
        warnings=warnings,
        info=info,
        is_conformant=len(errors) == 0,
        manifest_valid=manifest_valid,
    )


def _validate_against_schema(data: dict, schema: dict) -> None:
    """Lightweight required-properties check. Raises on failure."""
    required = schema.get("required", [])
    for req in required:
        if req not in data:
            msg = f"Missing required property: {req}"
            raise ValueError(msg)


def report_to_dict(report: ConformanceReport) -> dict:
    """Convert a ConformanceReport to a JSON-serializable dict.

    Args:
        report: The conformance report to serialize.

    Returns:
        A dict safe for json.dumps().
    """

    def _f2d(f: ConformanceFinding) -> dict:
        return {
            "table_name": f.table_name,
            "field_name": f.field_name,
            "level": f.level.value,
            "message": f.message,
            "check_id": f.check_id,
        }

    return {
        "tables_checked": report.tables_checked,
        "tables_expected": report.tables_expected,
        "errors": [_f2d(f) for f in report.errors],
        "warnings": [_f2d(f) for f in report.warnings],
        "info": [_f2d(f) for f in report.info],
        "is_conformant": report.is_conformant,
        "manifest_valid": report.manifest_valid,
    }


# ---------------------------------------------------------------------------
# Markdown generation
# ---------------------------------------------------------------------------


def generate_reference_markdown(
    non_empty_types: list[str],
    present_but_inactive: dict[str, list[str]] | None = None,
) -> str:
    """Generate human-readable intermediate format reference.

    Args:
        non_empty_types: PSS/E record type names to include.
        present_but_inactive: Optional dict of inactive fields.

    Returns:
        A complete markdown string.
    """
    all_schemas = {ts.record_type: ts for ts in get_table_schemas()}

    lines: list[str] = [
        "# Intermediate Format Reference",
        "",
        "## Schema Version",
        "",
        "1.0.0",
        "",
        "## System Metadata",
        "",
        "- **SBASE**: System MVA base (from PSS/E header)",
        "- **BASFRQ**: Base frequency in Hz",
        "- **REV**: PSS/E revision number (31.x)",
        "",
        "## Per-Unit Convention Reference",
        "",
        "| Base | Description |",
        "|------|-------------|",
        "| system_mva | System MVA base (SBASE) |",
        "| winding_mva | Winding-specific MVA base |",
        "| bus_kv | Bus base voltage (BASKV) |",
        "| none | Not a per-unit quantity |",
        "| mixed | Depends on mode code (CW/CZ/CM) |",
        "",
        "## Record Type Tables",
        "",
    ]

    inactive_all: dict[str, set[str]] = {}
    if present_but_inactive:
        for rt, fields in present_but_inactive.items():
            inactive_all[rt] = set(fields)

    preservation_summary: list[tuple[str, str, str]] = []

    for rt in non_empty_types:
        ts = all_schemas.get(rt)
        if ts is None:
            continue

        lines.append(f"### {rt}")
        lines.append("")
        lines.append(ts.description)
        lines.append("")
        lines.append(f"**Table name:** `{ts.table_name}`")
        lines.append(f"**Primary key:** `{ts.primary_key}`")
        if ts.multi_line_record:
            lines.append("**Multi-line record:** Yes")
        lines.append("")

        # Field table
        lines.append("| Field | Type | Unit | PU Base | Req | Description |")
        lines.append("|-------|------|------|--------|-----|-------------|")
        rt_inactive = inactive_all.get(rt, set())
        for f in ts.fields:
            req = "Y" if f.required else "N"
            desc = f.description
            if f.preservation_critical:
                desc = f"**[P]** {desc}"
                preservation_summary.append((rt, f.name, f.description))
            if f.name in rt_inactive:
                desc = f"{desc} *(inactive)*"
            unit = f.unit or "---"
            pub = f.per_unit_base.value
            lines.append(f"| {f.name} | {f.data_type} | {unit} | {pub} | {req} | {desc} |")

        lines.append("")
        if ts.notes:
            lines.append(f"**Notes:** {ts.notes}")
            lines.append("")

    # Appendix A: preservation
    lines.append("## Appendix A: Preservation Requirements Summary")
    lines.append("")
    if preservation_summary:
        lines.append("| Record Type | Field | Description |")
        lines.append("|-------------|-------|-------------|")
        for rt, fname, desc in preservation_summary:
            lines.append(f"| {rt} | {fname} | {desc} |")
    else:
        lines.append("No preservation-critical fields.")
    lines.append("")

    # Appendix B: inactive
    lines.append("## Appendix B: Present-But-Inactive Fields")
    lines.append("")
    if inactive_all:
        for rt, inactive_set in sorted(inactive_all.items()):
            lines.append(f"### {rt}")
            lines.append("")
            for fname in sorted(inactive_set):
                lines.append(f"- `{fname}`")
            lines.append("")
    else:
        lines.append("No inactive fields detected.")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for schema generation and validation.

    Args:
        argv: Command-line arguments. None reads sys.argv[1:].
    """
    parser = argparse.ArgumentParser(description="Intermediate Format Schema tools.")
    sub = parser.add_subparsers(dest="command", required=True)

    # Generate
    gen = sub.add_parser("generate", help="Generate schemas")
    gen.add_argument(
        "--raw-summary",
        required=True,
        help="Path to D3 raw counts JSON",
    )
    gen.add_argument(
        "--canonical-csvs",
        default=None,
        help="Canonical parser CSV directory",
    )
    gen.add_argument(
        "--parser-mapping",
        default=None,
        help="Record type mapping JSON",
    )
    gen.add_argument(
        "-o",
        "--output",
        default="data/fnm/intermediate",
        help="Output directory",
    )

    # Validate
    val = sub.add_parser("validate", help="Validate tables")
    val.add_argument(
        "--csv-dir",
        required=True,
        help="CSV tables directory",
    )
    val.add_argument(
        "--schema-dir",
        required=True,
        help="JSON Schema directory",
    )
    val.add_argument(
        "--manifest",
        required=True,
        help="Manifest JSON path",
    )
    val.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output directory",
    )

    args = parser.parse_args(argv)

    if args.command == "generate":
        _cmd_generate(args)
    elif args.command == "validate":
        _cmd_validate(args)


def _cmd_generate(args: argparse.Namespace) -> None:
    """Execute the 'generate' subcommand."""
    raw_path = Path(args.raw_summary)
    output_dir = Path(args.output)

    raw_data = json.loads(raw_path.read_text(encoding="utf-8"))
    non_empty = raw_data.get("non_empty_sections", [])

    inactive: dict[str, list[str]] | None = None
    if args.canonical_csvs:
        csv_dir = Path(args.canonical_csvs)
        rt_to_tn: dict[str, str] = {rt: _record_type_to_table_name(rt) for rt in non_empty}
        if args.parser_mapping:
            mapping = json.loads(Path(args.parser_mapping).read_text(encoding="utf-8"))
            rt_to_tn.update(mapping)
        inactive = detect_inactive_fields(csv_dir, non_empty, rt_to_tn)

    written = write_schemas(output_dir, non_empty, inactive)
    schema_dir = output_dir / "schemas"
    print(f"Wrote {len(written)} schemas to {schema_dir}")

    md = generate_reference_markdown(non_empty, inactive)
    md_path = output_dir / "intermediate_format_reference.md"
    md_path.write_text(md, encoding="utf-8")
    print(f"Wrote reference to {md_path}")


def _cmd_validate(args: argparse.Namespace) -> None:
    """Execute the 'validate' subcommand."""
    csv_dir = Path(args.csv_dir)
    schema_dir = Path(args.schema_dir)
    manifest_path = Path(args.manifest)

    report = validate_tables(csv_dir, schema_dir, manifest_path)
    result = report_to_dict(report)

    out = Path(args.output) if args.output else manifest_path.parent
    out.mkdir(parents=True, exist_ok=True)
    rpath = out / "conformance_report.json"
    rpath.write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote conformance report to {rpath}")

    status = "CONFORMANT" if report.is_conformant else "NON-CONFORMANT"
    print(
        f"Result: {status} "
        f"(errors={len(report.errors)}, "
        f"warnings={len(report.warnings)}, "
        f"info={len(report.info)})"
    )


if __name__ == "__main__":
    main()
