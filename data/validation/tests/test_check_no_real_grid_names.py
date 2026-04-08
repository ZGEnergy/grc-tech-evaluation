"""Tests for scripts/check_no_real_grid_names.py."""

from __future__ import annotations

from pathlib import Path

from scripts.check_no_real_grid_names import main, scan_file


def _token(*parts: str) -> str:
    return "".join(parts)


def _phrase(*parts: str) -> str:
    return " ".join(parts)


def test_scan_file_flags_real_operator_acronym(tmp_path: Path) -> None:
    path = tmp_path / "sample.md"
    term = _token("CA", "ISO")
    path.write_text(f"This example copied {term} nomenclature.\n", encoding="utf-8")

    violations = scan_file(path)

    assert len(violations) == 1
    assert violations[0].term == term
    assert violations[0].line_number == 1


def test_scan_file_flags_region_phrase_case_insensitively(tmp_path: Path) -> None:
    path = tmp_path / "sample.txt"
    term = _phrase("Western", "Electricity", "Coordinating", "Council").lower()
    path.write_text(
        f"The source mentioned {term} data.\n",
        encoding="utf-8",
    )

    violations = scan_file(path)

    assert len(violations) == 1
    assert violations[0].term.lower() == term


def test_scan_file_ignores_generic_iso_wording(tmp_path: Path) -> None:
    path = tmp_path / "sample.md"
    path.write_text(
        "Use a generic ISO market operator description, not a named entity.\n",
        encoding="utf-8",
    )

    assert scan_file(path) == []


def test_scan_file_avoids_false_positive_on_rf_string_prefix(tmp_path: Path) -> None:
    path = tmp_path / "sample.py"
    path.write_text('pattern = rf"^line$"\n', encoding="utf-8")

    assert scan_file(path) == []


def test_main_returns_nonzero_when_violation_found(tmp_path: Path) -> None:
    bad = tmp_path / "bad.md"
    good = tmp_path / "good.md"
    bad.write_text(
        f"Reference to {_token('ER', 'COT')} should fail.\n",
        encoding="utf-8",
    )
    good.write_text("Synthetic balancing area.\n", encoding="utf-8")

    exit_code = main([str(good), str(bad)])

    assert exit_code == 1
