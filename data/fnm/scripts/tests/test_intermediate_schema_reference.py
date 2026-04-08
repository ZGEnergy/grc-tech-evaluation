"""Tests for PRD 02/01 -- Intermediate Format Schema Reference.

Validates the document at data/fnm/docs/intermediate-schema.md for structural
completeness and consistency with Phase 1 D7 JSON Schema files.

These tests do NOT require FNM_PATH -- they validate the documentation artifact,
not FNM data.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths (relative to repo root)
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_DOC_PATH = _REPO_ROOT / "fnm" / "docs" / "intermediate-schema.md"
_SCHEMA_DIR = _REPO_ROOT / "fnm" / "intermediate" / "schemas"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_doc() -> str:
    """Read the intermediate schema reference document."""
    assert _DOC_PATH.exists(), f"Document not found: {_DOC_PATH}"
    return _DOC_PATH.read_text(encoding="utf-8")


def _schema_files() -> list[Path]:
    """Return all non-manifest JSON Schema files."""
    return sorted(p for p in _SCHEMA_DIR.glob("*.schema.json") if p.name != "manifest.schema.json")


def _load_schema(path: Path) -> dict:
    """Load and parse a JSON Schema file."""
    return json.loads(path.read_text(encoding="utf-8"))


def _table_name_to_record_type(schema: dict) -> str:
    """Extract the record type (title) from a JSON Schema."""
    return schema.get("title", "")


def _parse_table_summary(doc: str) -> list[dict[str, str]]:
    """Parse the Table Summary section into a list of row dicts."""
    # Find the table summary section
    match = re.search(
        r"## Table Summary\s*\n(.*?)(?=\n## [^#]|\Z)",
        doc,
        re.DOTALL,
    )
    assert match, "Table Summary section not found"
    section = match.group(1)

    # Parse markdown table rows
    rows = []
    in_table = False
    for line in section.strip().split("\n"):
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if not in_table:
            # Header row
            in_table = True
            continue
        if all(c.replace("-", "").replace(" ", "") == "" for c in cells):
            # Separator row
            continue
        if len(cells) >= 6:
            rows.append(
                {
                    "table": cells[0].strip("`"),
                    "record_type": cells[1],
                    "records": cells[2],
                    "columns": cells[3],
                    "primary_key": cells[4],
                    "purpose": cells[5],
                }
            )
    return rows


def _parse_h2_sections(doc: str) -> list[str]:
    """Extract all H2 section headings from the document."""
    return re.findall(r"^## (.+)$", doc, re.MULTILINE)


def _parse_field_table(section_text: str) -> list[dict[str, str]]:
    """Parse a field description table from a section."""
    # Find the ### Fields subsection
    match = re.search(
        r"### Fields\s*\n(.*?)(?=\n### |\Z)",
        section_text,
        re.DOTALL,
    )
    if not match:
        return []
    table_text = match.group(1)

    rows = []
    headers: list[str] = []
    for line in table_text.strip().split("\n"):
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if not headers:
            headers = cells
            continue
        if all(c.replace("-", "").replace(" ", "") == "" for c in cells):
            continue
        row = {}
        for i, h in enumerate(headers):
            row[h] = cells[i] if i < len(cells) else ""
        rows.append(row)
    return rows


def _get_section_text(doc: str, heading: str) -> str:
    """Extract the text of a specific H2 section."""
    pattern = rf"^## {re.escape(heading)}\s*$(.*?)(?=^## [^#]|\Z)"
    match = re.search(pattern, doc, re.MULTILINE | re.DOTALL)
    return match.group(1) if match else ""


def _parse_appendix_table(doc: str, appendix_heading: str) -> list[dict[str, str]]:
    """Parse a table from an appendix section."""
    section = _get_section_text(doc, appendix_heading)
    rows = []
    headers: list[str] = []
    for line in section.strip().split("\n"):
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if not headers:
            headers = cells
            continue
        if all(c.replace("-", "").replace(" ", "") == "" for c in cells):
            continue
        row = {}
        for i, h in enumerate(headers):
            row[h] = cells[i] if i < len(cells) else ""
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def doc() -> str:
    """Read the document once per module."""
    return _read_doc()


@pytest.fixture(scope="module")
def schema_files() -> list[Path]:
    """List all non-manifest schema files."""
    files = _schema_files()
    assert len(files) > 0, f"No schema files found in {_SCHEMA_DIR}"
    return files


@pytest.fixture(scope="module")
def schemas(schema_files: list[Path]) -> dict[str, dict]:
    """Load all schemas keyed by table name."""
    result = {}
    for p in schema_files:
        table_name = p.stem.replace(".schema", "")
        result[table_name] = _load_schema(p)
    return result


@pytest.fixture(scope="module")
def table_summary(doc: str) -> list[dict[str, str]]:
    """Parse the Table Summary."""
    return _parse_table_summary(doc)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDocumentExists:
    """T01: Document exists and is non-empty."""

    def test_document_exists(self) -> None:
        assert _DOC_PATH.exists(), f"Document not found: {_DOC_PATH}"
        content = _DOC_PATH.read_text(encoding="utf-8")
        assert len(content) > 0, "Document is empty"


class TestTableSummary:
    """T02: Table Summary covers all non-empty record types."""

    def test_table_summary_covers_all_non_empty_types(
        self, table_summary: list[dict[str, str]], schema_files: list[Path]
    ) -> None:
        # Get table names from schema files
        schema_table_names = {p.stem.replace(".schema", "") for p in schema_files}
        # Get table names from summary
        summary_table_names = {row["table"] for row in table_summary}
        assert schema_table_names == summary_table_names, (
            f"Mismatch: in schema but not summary: {schema_table_names - summary_table_names}, "
            f"in summary but not schema: {summary_table_names - schema_table_names}"
        )


class TestSectionStructure:
    """T03: Every table has a dedicated H2 section."""

    def test_every_table_has_dedicated_section(self, doc: str, schemas: dict[str, dict]) -> None:
        h2_headings = _parse_h2_sections(doc)
        for table_name, schema in schemas.items():
            record_type = _table_name_to_record_type(schema)
            assert record_type in h2_headings, (
                f"Missing H2 section for record type '{record_type}' (table '{table_name}')"
            )


class TestFieldCoverage:
    """T04: Field tables cover all schema fields."""

    def test_field_tables_cover_all_schema_fields(self, doc: str, schemas: dict[str, dict]) -> None:
        for table_name, schema in schemas.items():
            record_type = _table_name_to_record_type(schema)
            section = _get_section_text(doc, record_type)
            assert section, f"Section for '{record_type}' not found"

            field_rows = _parse_field_table(section)
            doc_fields = {row["Field"].strip("`") for row in field_rows}
            schema_fields = set(schema.get("properties", {}).keys())

            missing = schema_fields - doc_fields
            assert not missing, f"Table '{record_type}': fields in schema but not in doc: {missing}"


class TestFieldTableColumns:
    """T05: Field tables have all required columns."""

    REQUIRED_COLUMNS = {
        "Field",
        "Type",
        "Unit",
        "Semantic Description",
        "Expected Range",
        "Nullable",
        "Default",
        "Evaluate-Tool Guidance",
    }

    def test_field_tables_have_required_columns(self, doc: str, schemas: dict[str, dict]) -> None:
        for table_name, schema in schemas.items():
            record_type = _table_name_to_record_type(schema)
            section = _get_section_text(doc, record_type)
            if not section:
                continue

            # Extract header row from field table
            fields_match = re.search(
                r"### Fields\s*\n(.*?)(?=\n### |\Z)",
                section,
                re.DOTALL,
            )
            assert fields_match, f"No Fields subsection in '{record_type}'"
            table_text = fields_match.group(1)

            # Parse header
            for line in table_text.strip().split("\n"):
                line = line.strip()
                if line.startswith("|") and "Field" in line:
                    headers = {c.strip() for c in line.split("|")[1:-1]}
                    missing = self.REQUIRED_COLUMNS - headers
                    assert not missing, f"Table '{record_type}': missing columns: {missing}"
                    break


class TestFieldTypes:
    """T06: Field types match schema definitions."""

    def test_field_types_match_schema(self, doc: str, schemas: dict[str, dict]) -> None:
        for table_name, schema in schemas.items():
            record_type = _table_name_to_record_type(schema)
            section = _get_section_text(doc, record_type)
            if not section:
                continue

            field_rows = _parse_field_table(section)
            props = schema.get("properties", {})

            for row in field_rows:
                fname = row["Field"].strip("`")
                doc_type = row["Type"].strip()
                if fname in props:
                    schema_type = props[fname].get("type", "")
                    assert doc_type == schema_type, (
                        f"Table '{record_type}', field '{fname}': "
                        f"doc type '{doc_type}' != schema type '{schema_type}'"
                    )


class TestPreservationCritical:
    """T07: Preservation-critical fields are annotated."""

    def test_preservation_critical_fields_annotated(
        self, doc: str, schemas: dict[str, dict]
    ) -> None:
        for table_name, schema in schemas.items():
            record_type = _table_name_to_record_type(schema)
            section = _get_section_text(doc, record_type)
            if not section:
                continue

            field_rows = _parse_field_table(section)
            props = schema.get("properties", {})

            for fname, fdef in props.items():
                if fdef.get("x-psse-preservation-critical", False):
                    # Find the matching row
                    matching = [r for r in field_rows if r["Field"].strip("`") == fname]
                    assert matching, (
                        f"Table '{record_type}': preservation-critical field "
                        f"'{fname}' not found in field table"
                    )
                    desc = matching[0].get("Semantic Description", "")
                    assert "**[preservation-critical]**" in desc, (
                        f"Table '{record_type}', field '{fname}': missing "
                        f"**[preservation-critical]** annotation in Semantic Description"
                    )


class TestWorkedExamples:
    """T08-T10: Worked examples validation."""

    def test_every_section_has_worked_example(self, doc: str, schemas: dict[str, dict]) -> None:
        for table_name, schema in schemas.items():
            record_type = _table_name_to_record_type(schema)
            section = _get_section_text(doc, record_type)
            assert section, f"Section for '{record_type}' not found"
            assert "### Worked Example" in section, (
                f"Table '{record_type}': missing ### Worked Example subsection"
            )
            # Check for fenced code block
            example_match = re.search(
                r"### Worked Example.*?```(.*?)```",
                section,
                re.DOTALL,
            )
            assert example_match, f"Table '{record_type}': no fenced code block in Worked Example"

    def test_worked_examples_include_primary_key(self, doc: str, schemas: dict[str, dict]) -> None:
        for table_name, schema in schemas.items():
            record_type = _table_name_to_record_type(schema)
            section = _get_section_text(doc, record_type)
            if not section:
                continue

            # Get primary key from header block
            pk_match = re.search(r"\*\*Primary key:\*\*\s*`\[([^\]]+)\]`", section)
            if not pk_match:
                continue
            pk_fields = [f.strip() for f in pk_match.group(1).split(",")]

            # Get worked example content
            example_match = re.search(
                r"### Worked Example.*?```(.*?)```",
                section,
                re.DOTALL,
            )
            if not example_match:
                continue
            example_text = example_match.group(1)

            for pk_field in pk_fields:
                # Check field appears with a value
                pattern = rf"^\s*{re.escape(pk_field)}:\s*\S"
                assert re.search(pattern, example_text, re.MULTILINE), (
                    f"Table '{record_type}': primary key field '{pk_field}' "
                    f"missing or empty in worked example"
                )

    def test_worked_examples_use_plausible_bus_voltages(
        self, doc: str, schemas: dict[str, dict]
    ) -> None:
        valid_kv = {69, 115, 138, 230, 345, 500}

        # Check Bus table BASKV
        bus_section = _get_section_text(doc, "Bus")
        if bus_section:
            example_match = re.search(
                r"### Worked Example.*?```(.*?)```",
                bus_section,
                re.DOTALL,
            )
            if example_match:
                for line in example_match.group(1).split("\n"):
                    if "BASKV:" in line:
                        val = float(line.split(":")[1].strip())
                        assert val in valid_kv, (
                            f"Bus BASKV={val} not in standard voltages {valid_kv}"
                        )

        # Check Transformer NOMV1, NOMV2
        xfmr_section = _get_section_text(doc, "Transformer")
        if xfmr_section:
            example_match = re.search(
                r"### Worked Example.*?```(.*?)```",
                xfmr_section,
                re.DOTALL,
            )
            if example_match:
                for line in example_match.group(1).split("\n"):
                    for field in ("NOMV1:", "NOMV2:"):
                        if field in line:
                            val = float(line.split(":")[1].strip())
                            if val > 0:  # 0 means use bus base kV
                                assert val in valid_kv, (
                                    f"Transformer {field.rstrip(':')}={val} "
                                    f"not in standard voltages {valid_kv}"
                                )


class TestGuidanceQuality:
    """T11: Evaluate-tool guidance is non-generic."""

    GENERIC_PHRASES = [
        "check that values are correct",
        "verify the value",
        "ensure correctness",
    ]

    def test_evaluate_tool_guidance_non_generic(self, doc: str, schemas: dict[str, dict]) -> None:
        for table_name, schema in schemas.items():
            record_type = _table_name_to_record_type(schema)
            section = _get_section_text(doc, record_type)
            if not section:
                continue

            field_rows = _parse_field_table(section)
            for row in field_rows:
                fname = row["Field"].strip("`")
                guidance = row.get("Evaluate-Tool Guidance", "")
                assert guidance.strip(), (
                    f"Table '{record_type}', field '{fname}': Evaluate-Tool Guidance is empty"
                )
                for phrase in self.GENERIC_PHRASES:
                    assert phrase.lower() not in guidance.lower(), (
                        f"Table '{record_type}', field '{fname}': "
                        f"generic guidance phrase '{phrase}' found"
                    )


class TestAppendixPreservationCritical:
    """T12: Appendix lists all preservation-critical fields."""

    def test_appendix_preservation_critical_complete(
        self, doc: str, schemas: dict[str, dict]
    ) -> None:
        # Count preservation-critical fields across all schemas
        expected: set[tuple[str, str]] = set()
        for table_name, schema in schemas.items():
            record_type = _table_name_to_record_type(schema)
            for fname, fdef in schema.get("properties", {}).items():
                if fdef.get("x-psse-preservation-critical", False):
                    expected.add((record_type, fname))

        # Parse appendix table
        appendix_rows = _parse_appendix_table(doc, "Appendix: Preservation-Critical Fields")
        found: set[tuple[str, str]] = set()
        for row in appendix_rows:
            rt = row.get("Record Type", "")
            field = row.get("Field", "").strip("`")
            found.add((rt, field))

        missing = expected - found
        assert not missing, f"Preservation-critical fields missing from appendix: {missing}"
        assert len(found) == len(expected), (
            f"Count mismatch: appendix has {len(found)}, schemas have {len(expected)}"
        )


class TestAppendixInactiveFields:
    """T13: Appendix lists all present-but-inactive fields."""

    def test_appendix_inactive_fields_complete(self, doc: str, schemas: dict[str, dict]) -> None:
        expected: set[tuple[str, str]] = set()
        for table_name, schema in schemas.items():
            record_type = _table_name_to_record_type(schema)
            for fname, fdef in schema.get("properties", {}).items():
                if fdef.get("x-psse-present-but-inactive", False):
                    expected.add((record_type, fname))

        appendix_rows = _parse_appendix_table(doc, "Appendix: Present-but-Inactive Fields")
        found: set[tuple[str, str]] = set()
        for row in appendix_rows:
            rt = row.get("Record Type", "")
            field = row.get("Field", "").strip("`")
            found.add((rt, field))

        missing = expected - found
        assert not missing, f"Present-but-inactive fields missing from appendix: {missing}"
        assert len(found) == len(expected), (
            f"Count mismatch: appendix has {len(found)}, schemas have {len(expected)}"
        )


class TestSchemaReferences:
    """T14: Schema cross-references are valid."""

    def test_schema_cross_references_valid(self, doc: str, schema_files: list[Path]) -> None:
        # Find all schema file references in the document
        refs = set(re.findall(r"\.\.\/intermediate\/schemas\/(\w+\.schema\.json)", doc))

        # Verify each referenced file exists
        for ref in refs:
            path = _SCHEMA_DIR / ref
            assert path.exists(), f"Referenced schema file does not exist: {path}"

        # Verify every schema file is in the cross-reference index
        index_section = _get_section_text(doc, "Appendix: Schema Cross-Reference Index")
        schema_file_names = {p.name for p in schema_files}
        for fname in schema_file_names:
            assert fname in index_section, (
                f"Schema file '{fname}' not found in Schema Cross-Reference Index appendix"
            )
