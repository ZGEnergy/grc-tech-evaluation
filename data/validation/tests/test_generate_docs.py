"""Tests for Dataset Documentation & CLAUDE.md Update (PRD 05/08)."""

from __future__ import annotations

import textwrap
from pathlib import Path

from scripts.generate_docs import (
    DirectoryTreeEntry,
    NetworkId,
    NetworkSummary,
    apply_claude_md_update,
    build_claude_md_update,
    build_file_type_docs,
    build_known_limitations,
    build_provenance_entries,
    build_regeneration_steps,
    compute_network_summary,
    generate_docs,
    render_directory_tree,
    render_schema_reference,
    render_summary_table,
    walk_timeseries_tree,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    """Write a minimal CSV file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [",".join(header)]
    for row in rows:
        lines.append(",".join(row))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _create_m_file(path: Path) -> None:
    """Write a minimal MATPOWER .m file with known counts."""
    path.parent.mkdir(parents=True, exist_ok=True)
    content = textwrap.dedent("""\
        function mpc = case_test
        mpc.bus = [
        1 1 100 0 0 0 1 1.0 0 100 1 1.1 0.9;
        2 1 200 0 0 0 1 1.0 0 100 1 1.1 0.9;
        3 1 0 0 0 0 1 1.0 0 100 1 1.1 0.9;
        4 1 50 0 0 0 1 1.0 0 100 1 1.1 0.9;
        5 1 150 0 0 0 1 1.0 0 100 1 1.1 0.9;
        ];
        mpc.gen = [
        1 100 0 300 -300 1.0 100 1 500 0;
        2 200 0 300 -300 1.0 100 1 500 0;
        3 50 0 300 -300 1.0 100 1 500 0;
        ];
        mpc.branch = [
        1 2 0.01 0.1 0 250 250 250 0 0 1 -360 360;
        2 3 0.01 0.1 0 250 250 250 0 0 1 -360 360;
        3 4 0.01 0.1 0 250 250 250 0 0 1 -360 360;
        4 5 0.01 0.1 0 250 250 250 0 0 1 -360 360;
        ];
    """)
    path.write_text(content, encoding="utf-8")


def _setup_network_dir(tmp_path: Path, network_name: str) -> tuple[Path, Path]:
    """Create a minimal network data structure for testing.

    Returns (timeseries_dir, networks_dir).
    """
    ts_dir = tmp_path / "timeseries"
    net_dir = ts_dir / network_name
    net_dir.mkdir(parents=True)
    networks_dir = tmp_path / "networks"
    networks_dir.mkdir(parents=True)

    # Create .m file
    _create_m_file(networks_dir / f"{network_name}.m")

    # Create load_24h.csv
    hr_cols = [f"HR_{h}" for h in range(1, 25)]
    header = ["bus_id"] + hr_cols
    load_vals = ["100.0"] * 24
    _create_csv(net_dir / "load_24h.csv", header, [["1"] + load_vals])

    # Create bess_units.csv
    _create_csv(
        net_dir / "bess_units.csv",
        [
            "unit_id",
            "bus_id",
            "power_mw",
            "energy_mwh",
            "efficiency",
            "min_soc",
            "max_soc",
            "init_soc",
        ],
        [["BESS_1", "1", "50.0", "200.0", "0.9", "0.1", "0.9", "0.5"]],
    )

    # Create dr_buses.csv
    _create_csv(
        net_dir / "dr_buses.csv",
        ["bus_id", "max_curtailment_mw", "curtailment_cost", "max_hours"],
        [
            ["1", "10.0", "100.0", "4.0"],
            ["2", "20.0", "150.0", "6.0"],
        ],
    )

    # Create flowgates.csv
    _create_csv(
        net_dir / "flowgates.csv",
        ["flowgate_id", "line_ids", "weights", "limit_mw"],
        [
            ["FG_1", "1;2", "1.0;0.5", "500.0"],
            ["FG_2", "3;4", "0.8;0.3", "300.0"],
            ["FG_3", "1;3", "1.0;1.0", "400.0"],
        ],
    )

    return ts_dir, networks_dir


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestWalkTimeseriesTree:
    """test_walk_timeseries_tree_finds_all_entries"""

    def test_walk_timeseries_tree_finds_all_entries(self, tmp_path: Path) -> None:
        """Temp dir with 3 networks, CSVs, scenarios subdir -> all entries found, sorted."""
        ts_dir = tmp_path / "timeseries"
        for net in ["ACTIVSg10k", "ACTIVSg2000", "case39"]:
            net_dir = ts_dir / net
            net_dir.mkdir(parents=True)
            (net_dir / "load_24h.csv").write_text("bus_id\n1\n", encoding="utf-8")
            (net_dir / "bess_units.csv").write_text("unit_id\nB1\n", encoding="utf-8")
            scenarios = net_dir / "scenarios"
            scenarios.mkdir()
            (scenarios / "scenario_multipliers_wind_50x24.csv").write_text(
                "scenario_id\n1\n", encoding="utf-8"
            )

        entries = walk_timeseries_tree(ts_dir)

        # Should find all directories and files
        assert len(entries) > 0

        # All 3 networks should appear
        rel_paths = [e.relative_path for e in entries]
        for net in ["ACTIVSg10k", "ACTIVSg2000", "case39"]:
            assert net in rel_paths

        # Directories first at each level
        dir_entries = [e for e in entries if e.is_directory and e.indent_level == 0]
        assert len(dir_entries) == 3

        # Files inside networks
        file_entries = [e for e in entries if not e.is_directory]
        assert len(file_entries) >= 3  # at least 1 csv per network

        # scenarios subdirs found
        scenario_dirs = [e for e in entries if e.is_directory and "scenarios" in e.relative_path]
        assert len(scenario_dirs) == 3

        # Entries are sorted (directories before files, alphabetical)
        dir_names = [e.relative_path for e in dir_entries]
        assert dir_names == sorted(dir_names)


class TestRenderDirectoryTree:
    """test_render_directory_tree_produces_valid_markdown"""

    def test_render_directory_tree_produces_valid_markdown(self) -> None:
        """Small entry list -> fenced code block output."""
        entries = [
            DirectoryTreeEntry("case39", True, "case39/", 0),
            DirectoryTreeEntry("case39/load_24h.csv", False, "load_24h.csv", 1),
            DirectoryTreeEntry("case39/scenarios", True, "scenarios/", 1),
            DirectoryTreeEntry("case39/scenarios/wind.csv", False, "wind.csv", 2),
        ]

        result = render_directory_tree(entries)

        assert result.startswith("```")
        assert result.endswith("```")
        assert "data/timeseries/" in result
        assert "case39/" in result
        assert "load_24h.csv" in result
        assert "scenarios/" in result


class TestBuildFileTypeDocs:
    """test_build_file_type_docs_covers_all_csv_types"""

    def test_build_file_type_docs_covers_all_csv_types(self) -> None:
        """Exactly 13 entries, load_24h has 25 columns."""
        docs = build_file_type_docs()

        assert len(docs) == 13

        # Check all file types present
        file_types = {d.file_type for d in docs}
        expected_types = {
            "load_24h",
            "wind_forecast_24h",
            "wind_actual_24h",
            "solar_forecast_24h",
            "solar_actual_24h",
            "gen_temporal_params",
            "gen_fuel_classification",
            "reserve_requirements_24h",
            "reserve_eligibility",
            "bess_units",
            "dr_buses",
            "flowgates",
            "scenario_multipliers",
        }
        assert file_types == expected_types

        # load_24h should have 25 columns (bus_id + HR_1..HR_24)
        load_doc = [d for d in docs if d.file_type == "load_24h"][0]
        assert len(load_doc.columns) == 25


class TestRenderSchemaReference:
    """test_render_schema_reference_contains_tables"""

    def test_render_schema_reference_contains_tables(self) -> None:
        """13 tables with Column/Type/Unit/Description headers."""
        docs = build_file_type_docs()
        result = render_schema_reference(docs)

        # Should have 13 tables
        assert result.count("| Column | Type | Unit | Description |") == 13

        # Each table has separator row
        assert result.count("|--------|------|------|-------------|") == 13

        # All file types mentioned
        for doc in docs:
            assert f"### {doc.file_type}" in result


class TestComputeNetworkSummary:
    """test_compute_network_summary_from_data and test_compute_network_summary_missing_files"""

    def test_compute_network_summary_from_data(self, tmp_path: Path) -> None:
        """Temp data files -> correct counts (bus=5, bess=1, etc.)."""
        ts_dir, networks_dir = _setup_network_dir(tmp_path, "case39")

        summary = compute_network_summary(NetworkId.TINY, ts_dir, networks_dir)

        assert summary.network_id == NetworkId.TINY
        assert summary.bus_count == 5
        assert summary.gen_count == 3
        assert summary.branch_count == 4
        assert summary.bess_unit_count == 1
        assert summary.total_bess_power_mw == 50.0
        assert summary.total_bess_energy_mwh == 200.0
        assert summary.dr_bus_count == 2
        assert summary.total_dr_curtailment_mw == 30.0
        assert summary.flowgate_count == 3

    def test_compute_network_summary_missing_files(self, tmp_path: Path) -> None:
        """Only load_24h.csv -> zeros for missing, no error."""
        ts_dir = tmp_path / "timeseries"
        net_dir = ts_dir / "case39"
        net_dir.mkdir(parents=True)
        networks_dir = tmp_path / "networks"
        networks_dir.mkdir(parents=True)

        # Only create load_24h.csv
        hr_cols = [f"HR_{h}" for h in range(1, 25)]
        header = ["bus_id"] + hr_cols
        _create_csv(
            net_dir / "load_24h.csv",
            header,
            [["1"] + ["100.0"] * 24],
        )

        summary = compute_network_summary(NetworkId.TINY, ts_dir, networks_dir)

        assert summary.bess_unit_count == 0
        assert summary.total_bess_power_mw == 0.0
        assert summary.total_bess_energy_mwh == 0.0
        assert summary.dr_bus_count == 0
        assert summary.total_dr_curtailment_mw == 0.0
        assert summary.flowgate_count == 0
        assert summary.scenario_count_wind == 0
        assert summary.scenario_count_solar == 0
        assert summary.bus_count == 0  # no .m file
        assert summary.peak_load_mw == 100.0


class TestRenderSummaryTable:
    """test_render_summary_table_markdown_format"""

    def test_render_summary_table_markdown_format(self) -> None:
        """2 summaries -> valid markdown table."""
        summaries = [
            NetworkSummary(
                network_id=NetworkId.TINY,
                display_name="case39",
                bus_count=39,
                gen_count=10,
                branch_count=46,
                peak_load_mw=6097.0,
                total_renewable_capacity_mw=1000.0,
                renewable_penetration_pct=16.4,
                bess_unit_count=2,
                total_bess_power_mw=100.0,
                total_bess_energy_mwh=400.0,
                dr_bus_count=5,
                total_dr_curtailment_mw=50.0,
                flowgate_count=3,
                scenario_count_wind=50,
                scenario_count_solar=50,
            ),
            NetworkSummary(
                network_id=NetworkId.SMALL,
                display_name="ACTIVSg2000",
                bus_count=2000,
                gen_count=544,
                branch_count=3206,
                peak_load_mw=55000.0,
                total_renewable_capacity_mw=12000.0,
                renewable_penetration_pct=21.8,
                bess_unit_count=10,
                total_bess_power_mw=500.0,
                total_bess_energy_mwh=2000.0,
                dr_bus_count=20,
                total_dr_curtailment_mw=200.0,
                flowgate_count=8,
                scenario_count_wind=50,
                scenario_count_solar=50,
            ),
        ]

        result = render_summary_table(summaries)

        lines = result.strip().split("\n")
        assert len(lines) == 4  # header + separator + 2 data rows

        # Check table structure
        assert lines[0].startswith("| Network")
        assert lines[1].startswith("|---")
        assert "case39" in lines[2]
        assert "ACTIVSg2000" in lines[3]

        # All values present
        assert "39" in lines[2]
        assert "2000" in lines[3]


class TestBuildProvenanceEntries:
    """test_build_provenance_entries_has_three_sources"""

    def test_build_provenance_entries_has_three_sources(self) -> None:
        """ACTIVSg (SMALL/MEDIUM), RTS-GMLC (TINY), MATPOWER."""
        entries = build_provenance_entries()

        assert len(entries) == 3

        names = {e.source_name for e in entries}
        assert "ACTIVSg Synthetic Grid Cases" in names
        assert "RTS-GMLC" in names
        assert "MATPOWER" in names

        # Check network assignments
        activsg = [e for e in entries if "ACTIVSg" in e.source_name][0]
        assert NetworkId.SMALL in activsg.networks_used
        assert NetworkId.MEDIUM in activsg.networks_used

        rts = [e for e in entries if "RTS" in e.source_name][0]
        assert NetworkId.TINY in rts.networks_used

        matpower = [e for e in entries if "MATPOWER" in e.source_name][0]
        assert len(matpower.networks_used) == 3


class TestBuildKnownLimitations:
    """test_build_known_limitations_has_six_items"""

    def test_build_known_limitations_has_six_items(self) -> None:
        """6 documented limitations."""
        limitations = build_known_limitations()
        assert len(limitations) == 6

        # All have title, description, mitigation
        for lim in limitations:
            assert lim.title
            assert lim.description
            assert lim.mitigation


class TestBuildRegenerationSteps:
    """test_build_regeneration_steps_ordered"""

    def test_build_regeneration_steps_ordered(self) -> None:
        """>= 5 steps, sequential numbering."""
        steps = build_regeneration_steps()

        assert len(steps) >= 5

        # Sequential numbering
        for i, step in enumerate(steps, 1):
            assert step.step_number == i

        # All have required fields
        for step in steps:
            assert step.script_path
            assert step.description
            assert step.estimated_runtime


class TestApplyClaudeMdUpdate:
    """test_apply_claude_md_update_appends_section and test_apply_claude_md_update_idempotent"""

    def test_apply_claude_md_update_appends_section(self, tmp_path: Path) -> None:
        """Preserves existing content, adds ## Augmented Data."""
        claude_md = tmp_path / "CLAUDE.md"
        existing = "# My Project\n\nSome existing content.\n\n## Other Section\n\nDetails.\n"
        claude_md.write_text(existing, encoding="utf-8")

        update = build_claude_md_update()
        apply_claude_md_update(claude_md, update)

        result = claude_md.read_text(encoding="utf-8")

        # Existing content preserved
        assert "# My Project" in result
        assert "Some existing content." in result
        assert "## Other Section" in result

        # New section added
        assert "## Augmented Data" in result
        assert result.count("## Augmented Data") == 1

    def test_apply_claude_md_update_idempotent(self, tmp_path: Path) -> None:
        """Twice -> exactly one ## Augmented Data section."""
        claude_md = tmp_path / "CLAUDE.md"
        existing = "# My Project\n\nSome content.\n"
        claude_md.write_text(existing, encoding="utf-8")

        update = build_claude_md_update()

        # Apply twice
        apply_claude_md_update(claude_md, update)
        apply_claude_md_update(claude_md, update)

        result = claude_md.read_text(encoding="utf-8")

        # Exactly one occurrence
        assert result.count("## Augmented Data") == 1

        # Original content preserved
        assert "# My Project" in result


class TestGenerateDocsEndToEnd:
    """test_generate_docs_end_to_end"""

    def test_generate_docs_end_to_end(self, tmp_path: Path) -> None:
        """Temp repo structure -> README.md written, CLAUDE.md updated."""
        ts_dir, networks_dir = _setup_network_dir(tmp_path, "case39")

        readme_path = ts_dir / "README.md"
        claude_md_path = tmp_path / "CLAUDE.md"
        claude_md_path.write_text("# Test CLAUDE.md\n\nExisting content.\n", encoding="utf-8")

        generate_docs(
            timeseries_base_dir=ts_dir,
            networks_dir=networks_dir,
            readme_output_path=readme_path,
            claude_md_path=claude_md_path,
            repo_dir=tmp_path,
        )

        # README.md was written
        assert readme_path.exists()
        readme_text = readme_path.read_text(encoding="utf-8")
        assert "# Augmented Timeseries Data" in readme_text
        assert "## CSV Schema Reference" in readme_text
        assert "## Data Provenance" in readme_text
        assert "## Known Limitations" in readme_text
        assert "## Data Regeneration" in readme_text

        # CLAUDE.md was updated
        claude_text = claude_md_path.read_text(encoding="utf-8")
        assert "# Test CLAUDE.md" in claude_text
        assert "## Augmented Data" in claude_text
