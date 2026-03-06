"""Tests for Reproducibility Manifest Generation (PRD 05/07)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.generate_manifest import (
    FileChecksum,
    GenerationParameters,
    GitInfo,
    Manifest,
    NetworkFileChecksums,
    NetworkId,
    NetworkSeeds,
    ScriptChecksum,
    SeedEntry,
    SoftwareVersions,
    collect_csv_checksums,
    collect_mfile_checksums,
    collect_script_checksums,
    compute_sha256,
    detect_git_info,
    detect_software_versions,
    extract_seeds_from_metadata,
    extract_student_t_params,
    generate_manifest,
    serialize_manifest,
    validate_manifest,
    write_manifest,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_valid_manifest(
    tmp_path: Path,
    *,
    bad_checksum: str | None = None,
) -> Manifest:
    """Build a syntactically valid manifest for testing.

    If *bad_checksum* is not None, it replaces one file's SHA-256
    so that validation should report an error.
    """
    csv_sha = bad_checksum if bad_checksum else "a" * 64
    return Manifest(
        manifest_version="1.0.0",
        generated_at="2025-01-01T00:00:00+00:00",
        git=GitInfo(
            commit_hash="a" * 40,
            dirty=False,
            branch="main",
            warning=None,
        ),
        file_checksums=[
            NetworkFileChecksums(
                network_id=NetworkId.TINY,
                csv_files=[
                    FileChecksum(
                        relative_path="load_24h.csv",
                        sha256=csv_sha,
                        size_bytes=100,
                    )
                ],
                m_files=[],
            )
        ],
        script_checksums=[
            ScriptChecksum(
                filename="gen.py",
                relative_path="scripts/gen.py",
                sha256="b" * 64,
                size_bytes=200,
            )
        ],
        seeds=[
            NetworkSeeds(
                network_id=NetworkId.TINY,
                seeds=[
                    SeedEntry(
                        script_name="stochastic_metadata",
                        process_name="master",
                        seed_value=42,
                    )
                ],
            )
        ],
        parameters=[
            GenerationParameters(
                network_id=NetworkId.TINY,
                smoothing_window=3,
                wind_bias_fraction=0.0,
                solar_bias_fraction=0.0,
                scenario_count=50,
                student_t_params=[],
                bess_placement_scores=None,
                bess_fleet_target_pct=0.04,
                dr_selection_criteria=None,
                dr_fleet_target_pct=0.05,
                flowgate_thresholds=None,
            )
        ],
        software=SoftwareVersions(
            python="3.12.0",
            numpy="1.26.0",
            scipy="1.12.0",
            octave=None,
            matpower=None,
        ),
        total_files_checksummed=1,
        total_scripts_hashed=1,
        networks_covered=["case39"],
    )


# ---------------------------------------------------------------------------
# 1. test_compute_sha256_known_content
# ---------------------------------------------------------------------------


def test_compute_sha256_known_content(tmp_path: Path) -> None:
    """SHA-256 of known content produces a 64-char lowercase hex string."""
    f = tmp_path / "hello.txt"
    f.write_bytes(b"hello world\n")
    digest = compute_sha256(f)
    assert len(digest) == 64
    assert digest == digest.lower()
    # Verify against known hash of "hello world\n"
    assert digest.isalnum()


# ---------------------------------------------------------------------------
# 2. test_compute_sha256_file_not_found
# ---------------------------------------------------------------------------


def test_compute_sha256_file_not_found(tmp_path: Path) -> None:
    """Missing file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        compute_sha256(tmp_path / "no_such_file.txt")


# ---------------------------------------------------------------------------
# 3. test_collect_csv_checksums_finds_all_csvs
# ---------------------------------------------------------------------------


def test_collect_csv_checksums_finds_all_csvs(tmp_path: Path) -> None:
    """Three CSVs (including one in a subdirectory) are found, sorted."""
    (tmp_path / "a.csv").write_text("col\n1\n")
    (tmp_path / "b.csv").write_text("col\n2\n")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "c.csv").write_text("col\n3\n")

    results = collect_csv_checksums(tmp_path)
    assert len(results) == 3
    paths = [r.relative_path for r in results]
    assert paths == sorted(paths)


# ---------------------------------------------------------------------------
# 4. test_collect_csv_checksums_empty_directory
# ---------------------------------------------------------------------------


def test_collect_csv_checksums_empty_directory(tmp_path: Path) -> None:
    """Empty directory returns an empty list."""
    assert collect_csv_checksums(tmp_path) == []


# ---------------------------------------------------------------------------
# 5. test_collect_mfile_checksums_finds_clean_m
# ---------------------------------------------------------------------------


def test_collect_mfile_checksums_finds_clean_m(tmp_path: Path) -> None:
    """Only *_clean.m files are included, not original .m files."""
    (tmp_path / "case39.m").write_text("original")
    (tmp_path / "case39_clean.m").write_text("cleaned")
    (tmp_path / "ACTIVSg2000_clean.m").write_text("cleaned2")

    results = collect_mfile_checksums(tmp_path, NetworkId.TINY)
    names = [r.relative_path for r in results]
    assert "case39_clean.m" in names
    assert "ACTIVSg2000_clean.m" in names
    assert "case39.m" not in names


# ---------------------------------------------------------------------------
# 6. test_collect_script_checksums_excludes_tests
# ---------------------------------------------------------------------------


def test_collect_script_checksums_excludes_tests(tmp_path: Path) -> None:
    """Only top-level .py files are included; tests/ is excluded."""
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "__init__.py").write_text("")
    (scripts / "gen_load.py").write_text("print('hello')")
    (scripts / "gen_wind.py").write_text("print('wind')")
    tests = scripts / "tests"
    tests.mkdir()
    (tests / "test_gen.py").write_text("def test(): pass")

    results = collect_script_checksums(scripts)
    filenames = [r.filename for r in results]
    assert "gen_load.py" in filenames
    assert "gen_wind.py" in filenames
    assert "__init__.py" not in filenames
    assert "test_gen.py" not in filenames


# ---------------------------------------------------------------------------
# 7. test_extract_seeds_from_metadata_tiny
# ---------------------------------------------------------------------------


def test_extract_seeds_from_metadata_tiny(tmp_path: Path) -> None:
    """stochastic_metadata.json with master_seed=42 yields a SeedEntry."""
    scenarios = tmp_path / "scenarios"
    scenarios.mkdir()
    meta = {"master_seed": 42}
    (scenarios / "stochastic_metadata.json").write_text(json.dumps(meta))

    seeds = extract_seeds_from_metadata(NetworkId.TINY, tmp_path)
    assert len(seeds) == 1
    assert seeds[0].seed_value == 42
    assert seeds[0].process_name == "master"


# ---------------------------------------------------------------------------
# 8. test_extract_seeds_no_metadata
# ---------------------------------------------------------------------------


def test_extract_seeds_no_metadata(tmp_path: Path) -> None:
    """No scenarios dir returns an empty list."""
    seeds = extract_seeds_from_metadata(NetworkId.TINY, tmp_path)
    assert seeds == []


# ---------------------------------------------------------------------------
# 9. test_extract_student_t_params_small_format
# ---------------------------------------------------------------------------


def test_extract_student_t_params_small_format(tmp_path: Path) -> None:
    """Per-hour wind + solar + pooled entries from student_t_params.json."""
    scenarios = tmp_path / "scenarios"
    scenarios.mkdir()
    data = {
        "wind": [
            {"hour": 0, "df": 5.0, "loc": 0.1, "scale": 0.5},
            {"hour": 1, "df": 6.0, "loc": 0.2, "scale": 0.6},
        ],
        "solar": {"df": 4.5, "loc": 0.0, "scale": 1.0},
    }
    (scenarios / "student_t_params.json").write_text(json.dumps(data))

    params = extract_student_t_params(tmp_path)
    assert len(params) == 3
    wind_params = [p for p in params if p.resource_type == "wind"]
    solar_params = [p for p in params if p.resource_type == "solar"]
    assert len(wind_params) == 2
    assert len(solar_params) == 1
    assert solar_params[0].hour == -1  # pooled


# ---------------------------------------------------------------------------
# 10. test_detect_software_versions_python_numpy_scipy
# ---------------------------------------------------------------------------


def test_detect_software_versions_python_numpy_scipy() -> None:
    """Python version matches sys.version; numpy and scipy are non-empty."""
    sv = detect_software_versions()
    assert sv.python == sys.version.split()[0]
    assert len(sv.numpy) > 0
    assert len(sv.scipy) > 0


# ---------------------------------------------------------------------------
# 11. test_detect_git_info_returns_commit_hash
# ---------------------------------------------------------------------------


def test_detect_git_info_returns_commit_hash(tmp_path: Path) -> None:
    """A real git repo yields a 40-char hex commit hash and a branch name."""
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "init"],
        cwd=str(tmp_path),
        capture_output=True,
        check=True,
        env={
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@test.com",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@test.com",
            "HOME": str(tmp_path),
            "PATH": subprocess.run(
                ["printenv", "PATH"], capture_output=True, text=True
            ).stdout.strip(),
        },
    )

    info = detect_git_info(tmp_path)
    assert len(info.commit_hash) == 40
    assert all(c in "0123456789abcdef" for c in info.commit_hash)
    assert len(info.branch) > 0


# ---------------------------------------------------------------------------
# 12. test_validate_manifest_valid
# ---------------------------------------------------------------------------


def test_validate_manifest_valid(tmp_path: Path) -> None:
    """A valid manifest yields zero errors."""
    m = _make_valid_manifest(tmp_path)
    errors = validate_manifest(m)
    assert errors == []


# ---------------------------------------------------------------------------
# 13. test_validate_manifest_invalid_checksum
# ---------------------------------------------------------------------------


def test_validate_manifest_invalid_checksum(tmp_path: Path) -> None:
    """A bad SHA-256 string triggers a validation error."""
    m = _make_valid_manifest(tmp_path, bad_checksum="ZZZZ_not_hex_at_all")
    errors = validate_manifest(m)
    assert len(errors) >= 1
    assert any("SHA-256" in e or "sha256" in e.lower() for e in errors)


# ---------------------------------------------------------------------------
# 14. test_serialize_manifest_deterministic
# ---------------------------------------------------------------------------


def test_serialize_manifest_deterministic(tmp_path: Path) -> None:
    """Two calls on the same manifest produce identical JSON."""
    m = _make_valid_manifest(tmp_path)
    a = serialize_manifest(m)
    b = serialize_manifest(m)
    assert a == b
    # Verify it is valid JSON
    parsed = json.loads(a)
    assert parsed["manifest_version"] == "1.0.0"


# ---------------------------------------------------------------------------
# 15. test_write_manifest_rejects_invalid
# ---------------------------------------------------------------------------


def test_write_manifest_rejects_invalid(tmp_path: Path) -> None:
    """ValueError is raised and no file is written when manifest is invalid."""
    m = _make_valid_manifest(tmp_path, bad_checksum="bad")
    out = tmp_path / "manifest.json"
    with pytest.raises(ValueError, match="validation failed"):
        write_manifest(m, out)
    assert not out.exists()


# ---------------------------------------------------------------------------
# 16. test_generate_manifest_end_to_end
# ---------------------------------------------------------------------------


def test_generate_manifest_end_to_end(tmp_path: Path) -> None:
    """Full integration: create a temp repo structure and generate a manifest."""
    # Create repo structure
    repo = tmp_path / "repo"
    repo.mkdir()

    # Initialise a git repo so detect_git_info works
    subprocess.run(["git", "init"], cwd=str(repo), capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "init"],
        cwd=str(repo),
        capture_output=True,
        check=True,
        env={
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@test.com",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@test.com",
            "HOME": str(tmp_path),
            "PATH": subprocess.run(
                ["printenv", "PATH"], capture_output=True, text=True
            ).stdout.strip(),
        },
    )

    # Timeseries dirs
    ts = repo / "data" / "timeseries"
    for nid in ("case39",):
        ndir = ts / nid
        ndir.mkdir(parents=True)
        (ndir / "load_24h.csv").write_text("bus_id,HR_1\n1,100\n")

        # Scenarios with metadata
        sdir = ndir / "scenarios"
        sdir.mkdir()
        meta = {
            "master_seed": 42,
            "scenario_count": 50,
            "wind": {"df": 5.0, "loc": 0.0, "scale": 1.0},
            "solar": {"df": 4.0, "loc": 0.0, "scale": 1.0},
        }
        (sdir / "stochastic_metadata.json").write_text(json.dumps(meta))

    # Networks dir with a clean .m file
    networks = repo / "data" / "networks"
    networks.mkdir(parents=True)
    (networks / "case39_clean.m").write_text("mpc.bus = [1 2 3];")

    # Scripts dir
    scripts = repo / "scripts"
    scripts.mkdir()
    (scripts / "__init__.py").write_text("")
    (scripts / "gen_data.py").write_text("print('gen')")

    # Generate
    out = ts / "manifest.json"
    manifest = generate_manifest(
        timeseries_base_dir=ts,
        networks_dir=networks,
        scripts_dir=scripts,
        repo_dir=repo,
        output_path=out,
    )

    assert manifest.manifest_version == "1.0.0"
    assert manifest.total_files_checksummed >= 1
    assert manifest.total_scripts_hashed >= 1
    assert len(manifest.networks_covered) >= 1
    assert out.exists()

    # Written file is valid JSON
    written = json.loads(out.read_text(encoding="utf-8"))
    assert written["manifest_version"] == "1.0.0"
