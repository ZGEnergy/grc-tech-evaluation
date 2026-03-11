"""Tests for Makefile validate targets and CI workflow integration.

Covers 13 success criteria (T-D6.04-01 through T-D6.04-13) from the PRD.
File-check tests parse the Makefile and YAML directly; integration tests
(T-D6.04-12, T-D6.04-13) require a live build environment.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPORT_DIR = Path(__file__).resolve().parent.parent
MAKEFILE_PATH = REPORT_DIR / "Makefile"
WORKFLOW_PATH = REPORT_DIR.parent / ".github" / "workflows" / "deploy-report.yml"


@pytest.fixture()
def makefile_text() -> str:
    """Read the Makefile content."""
    return MAKEFILE_PATH.read_text()


@pytest.fixture()
def workflow_config() -> dict:
    """Parse the deploy-report.yml workflow."""
    return yaml.safe_load(WORKFLOW_PATH.read_text())


# ---------------------------------------------------------------------------
# Makefile structure tests
# ---------------------------------------------------------------------------


class TestMakefileTargets:
    """T-D6.04-01 through T-D6.04-07: Makefile validate targets."""

    def test_validate_target_exists(self, makefile_text: str) -> None:
        """T-D6.04-01: `validate` target is declared in .PHONY and defined."""
        assert "validate" in makefile_text
        # Confirm it appears in .PHONY line
        for line in makefile_text.splitlines():
            if line.startswith(".PHONY:"):
                targets = line.split(":", 1)[1].split()
                assert "validate" in targets
                break
        else:
            pytest.fail(".PHONY declaration not found")

    def test_validate_dev_target_exists(self, makefile_text: str) -> None:
        """T-D6.04-02: `validate-dev` target is declared in .PHONY and defined."""
        for line in makefile_text.splitlines():
            if line.startswith(".PHONY:"):
                targets = line.split(":", 1)[1].split()
                assert "validate-dev" in targets
                break
        else:
            pytest.fail(".PHONY declaration not found")

    def test_validate_depends_on_build(self, makefile_text: str) -> None:
        """T-D6.04-03: `validate` target depends on `build`."""
        for line in makefile_text.splitlines():
            if line.startswith("validate:"):
                assert "build" in line.split(":", 1)[1]
                return
        pytest.fail("validate target definition not found")

    def test_validate_dev_depends_on_build(self, makefile_text: str) -> None:
        """T-D6.04-04: `validate-dev` target depends on `build`."""
        for line in makefile_text.splitlines():
            if line.startswith("validate-dev:"):
                assert "build" in line.split(":", 1)[1]
                return
        pytest.fail("validate-dev target definition not found")

    def test_validate_runs_all_three_validators(self, makefile_text: str) -> None:
        """T-D6.04-05: `validate` recipe invokes all three validation scripts."""
        # Extract the validate recipe block (lines after "validate: build" until next target)
        recipe = _extract_recipe(makefile_text, "validate")
        assert "validate_links.py" in recipe
        assert "validate_chart_manifest.py" in recipe
        assert "validate_content.py" in recipe

    def test_validate_dev_runs_all_three_validators(self, makefile_text: str) -> None:
        """T-D6.04-06: `validate-dev` recipe invokes all three validation scripts."""
        recipe = _extract_recipe(makefile_text, "validate-dev")
        assert "validate_links.py" in recipe
        assert "validate_chart_manifest.py" in recipe
        assert "validate_content.py" in recipe

    def test_validate_dev_uses_allow_placeholders(self, makefile_text: str) -> None:
        """T-D6.04-07: `validate-dev` passes --allow-placeholders to validate_content.py."""
        recipe = _extract_recipe(makefile_text, "validate-dev")
        assert "--allow-placeholders" in recipe

    def test_validate_strict_no_allow_placeholders(self, makefile_text: str) -> None:
        """T-D6.04-08: strict `validate` does NOT pass --allow-placeholders."""
        recipe = _extract_recipe(makefile_text, "validate")
        assert "--allow-placeholders" not in recipe


# ---------------------------------------------------------------------------
# CI workflow tests
# ---------------------------------------------------------------------------


class TestWorkflowIntegration:
    """T-D6.04-09 through T-D6.04-11: GitHub Actions workflow updates."""

    def test_checkout_fetch_depth_zero(self, workflow_config: dict) -> None:
        """T-D6.04-09: Checkout step uses fetch-depth: 0."""
        steps = workflow_config["jobs"]["build"]["steps"]
        checkout_step = _find_step(steps, "actions/checkout")
        assert checkout_step is not None, "Checkout step not found"
        assert checkout_step.get("with", {}).get("fetch-depth") == 0

    def test_python_setup_present(self, workflow_config: dict) -> None:
        """T-D6.04-10: Python 3.12 setup step is present."""
        steps = workflow_config["jobs"]["build"]["steps"]
        python_step = _find_step(steps, "actions/setup-python")
        assert python_step is not None, "Python setup step not found"
        assert python_step.get("with", {}).get("python-version") == "3.12"

    def test_validate_step_present(self, workflow_config: dict) -> None:
        """T-D6.04-11: Workflow runs `make validate` between build and deploy."""
        steps = workflow_config["jobs"]["build"]["steps"]
        # Find the step that runs make validate
        validate_step = None
        validate_idx = None
        upload_idx = None
        for i, step in enumerate(steps):
            run_cmd = step.get("run", "")
            if "make validate" in run_cmd:
                validate_step = step
                validate_idx = i
            uses = step.get("uses", "")
            if "upload-pages-artifact" in uses:
                upload_idx = i

        assert validate_step is not None, "make validate step not found"
        assert validate_idx is not None
        assert upload_idx is not None
        assert validate_idx < upload_idx, "validate must run before upload"


# ---------------------------------------------------------------------------
# Integration tests (require live build environment)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestMakefileExecution:
    """T-D6.04-12 and T-D6.04-13: Live execution of Makefile targets."""

    def test_make_validate_dry_run(self) -> None:
        """T-D6.04-12: `make -n validate` shows expected commands without executing."""
        import subprocess

        result = subprocess.run(
            ["make", "-n", "validate"],
            capture_output=True,
            text=True,
            cwd=REPORT_DIR,
        )
        assert result.returncode == 0, f"make -n validate failed: {result.stderr}"
        assert "validate_links.py" in result.stdout
        assert "validate_chart_manifest.py" in result.stdout
        assert "validate_content.py" in result.stdout

    def test_make_validate_dev_dry_run(self) -> None:
        """T-D6.04-13: `make -n validate-dev` includes --allow-placeholders."""
        import subprocess

        result = subprocess.run(
            ["make", "-n", "validate-dev"],
            capture_output=True,
            text=True,
            cwd=REPORT_DIR,
        )
        assert result.returncode == 0, f"make -n validate-dev failed: {result.stderr}"
        assert "--allow-placeholders" in result.stdout


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_recipe(makefile_text: str, target: str) -> str:
    """Extract the recipe lines for a given Makefile target.

    Returns all tab-indented lines following the target definition, stopping
    at the next non-indented line or end of file.
    """
    lines = makefile_text.splitlines()
    in_recipe = False
    recipe_lines: list[str] = []
    for line in lines:
        if line.startswith(f"{target}:"):
            in_recipe = True
            continue
        if in_recipe:
            if line.startswith("\t") or line.startswith("    "):
                recipe_lines.append(line)
            elif line.strip() == "":
                # blank lines within recipe are OK
                continue
            else:
                break
    return "\n".join(recipe_lines)


def _find_step(steps: list[dict], uses_prefix: str) -> dict | None:
    """Find a workflow step by its `uses` prefix."""
    for step in steps:
        if step.get("uses", "").startswith(uses_prefix):
            return step
    return None
