from __future__ import annotations

from fnm.scripts.fnm_gating import (
    FnmFileCheck,
    FnmFileStatus,
    FnmPathResult,
    FnmPathStatus,
    find_repo_root,
    load_fnm_manifest,
    resolve_fnm_path,
)
from fnm.scripts.fnm_gating_cli import cli_validate_fnm_path
from fnm.scripts.fnm_gating_fixtures import require_fnm, require_fnm_csvs, require_fnm_raw
from fnm.scripts.gridcal_parser import (
    GRIDCAL_ELEMENT_COLLECTIONS,
    PSSE_TO_GRIDCAL_MAPPING,
    GridCalParserSummary,
    MultiCircuitCounts,
    ParserLog,
    ParserLogEntry,
    PsseIntermediateCounts,
    RecordTypeMapping,
    build_record_type_mapping,
)
from fnm.scripts.matpower_parser import (
    KnownLimitation,
    MatpowerParserLog,
    MatpowerParserSummary,
    ParserWarning,
    SectionCountMap,
    build_known_limitations,
    build_octave_command,
    find_matpower_path,
    log_to_dict,
    parse_octave_stdout,
    parse_octave_warnings,
    read_csv_field_counts,
    run_psse2mpc,
)
from fnm.scripts.matpower_parser import summary_to_dict as matpower_summary_to_dict
from fnm.scripts.raw_record_counter import (
    PSSE_V31_SECTION_NAMES,
    HeaderInfo,
    RecordCountSummary,
    count_raw_records,
    count_section_records,
    parse_header,
    summary_to_dict,
)

__all__ = [
    "FnmFileCheck",
    "FnmFileStatus",
    "FnmPathResult",
    "FnmPathStatus",
    "cli_validate_fnm_path",
    "find_repo_root",
    "load_fnm_manifest",
    "require_fnm",
    "require_fnm_csvs",
    "require_fnm_raw",
    "resolve_fnm_path",
    # matpower_parser
    "KnownLimitation",
    "MatpowerParserLog",
    "MatpowerParserSummary",
    "ParserWarning",
    "SectionCountMap",
    "build_known_limitations",
    "build_octave_command",
    "find_matpower_path",
    "log_to_dict",
    "matpower_summary_to_dict",
    "parse_octave_stdout",
    "parse_octave_warnings",
    "read_csv_field_counts",
    "run_psse2mpc",
    # gridcal_parser
    "GRIDCAL_ELEMENT_COLLECTIONS",
    "GridCalParserSummary",
    "MultiCircuitCounts",
    "PSSE_TO_GRIDCAL_MAPPING",
    "ParserLog",
    "ParserLogEntry",
    "PsseIntermediateCounts",
    "RecordTypeMapping",
    "build_record_type_mapping",
    # raw_record_counter
    "HeaderInfo",
    "PSSE_V31_SECTION_NAMES",
    "RecordCountSummary",
    "count_raw_records",
    "count_section_records",
    "parse_header",
    "summary_to_dict",
]
