"""Tests for PRD 04/03 — Grid Primer MDX Prose (SC-01 through SC-18)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPORT_DIR = Path(__file__).resolve().parent.parent
MDX_PATH = REPORT_DIR / "docs" / "grid-primer.mdx"
IMG_DIR = REPORT_DIR / "static" / "img" / "grid-primer"

STAGE_HEADINGS = [
    "## Stage 1: Single Generator, Single Load",
    "## Stage 2: Two Buses Connected by a Line",
    "## Stage 3: Meshed Network",
    "## Stage 4: Economic Dispatch and OPF",
    "## Stage 5: Transmission Limits and Congestion",
    "## Stage 6: Contingency Analysis and SCOPF",
]

PLACEHOLDER_TITLES = [
    "Set generator output and load demand; see real-time power balance",
    "Adjust line impedance and see how power flow changes",
    "Change injection at one bus and watch power redistribute across parallel paths",
    "Set generator costs and load level; see the optimal dispatch and resulting LMPs",
    "Toggle line limits on and off; watch LMPs diverge as congestion binds",
    "Trip a line and see how preventive SCOPF re-dispatches to maintain N-1 security",
]

SVG_SLUGS = [
    "stage-1_single-bus",
    "stage-2_two-bus",
    "stage-3_meshed-network",
    "stage-4_opf-dispatch",
    "stage-5_congestion",
    "stage-6_scopf",
]


@pytest.fixture(scope="module")
def mdx_text() -> str:
    return MDX_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def mdx_body(mdx_text: str) -> str:
    """MDX content without frontmatter."""
    parts = mdx_text.split("---", 2)
    assert len(parts) >= 3, "MDX file must have YAML frontmatter delimited by ---"
    return parts[2]


@pytest.fixture(scope="module")
def stage_sections(mdx_body: str) -> list[str]:
    """Extract the six stage sections from the MDX body."""
    pattern = r"(## Stage \d:.*?)(?=## (?:Stage \d|From Primer)|\Z)"
    sections = re.findall(pattern, mdx_body, re.DOTALL)
    return sections


def _count_prose_words(text: str) -> int:
    """Count words in prose, excluding frontmatter, MDX/JSX tags, code blocks, and math."""
    # Remove frontmatter
    text = re.sub(r"^---.*?---", "", text, count=1, flags=re.DOTALL)
    # Remove import lines
    text = re.sub(r"^import .*$", "", text, flags=re.MULTILINE)
    # Remove JSX comments
    text = re.sub(r"\{/\*.*?\*/\}", "", text, flags=re.DOTALL)
    # Remove code blocks
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    # Remove display math
    text = re.sub(r"\$\$.*?\$\$", "", text, flags=re.DOTALL)
    # Remove inline math
    text = re.sub(r"\$[^$]+?\$", "", text)
    # Remove JSX/HTML tags but keep text content
    text = re.sub(r"<[^>]+>", "", text)
    # Remove image references
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    # Remove markdown heading markers
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    return len(text.split())


def _get_section_between(body: str, start_heading: str, end_pattern: str) -> str:
    """Get text between a heading and the next matching pattern."""
    start_idx = body.find(start_heading)
    if start_idx == -1:
        return ""
    after_start = body[start_idx + len(start_heading) :]
    end_match = re.search(end_pattern, after_start, re.MULTILINE)
    if end_match:
        return after_start[: end_match.start()]
    return after_start


# --- SC-01: Word count in range (2000-3000) ---


def test_sc01_word_count_in_range(mdx_text: str) -> None:
    """SC-01: Total prose word count is between 2000 and 3000."""
    count = _count_prose_words(mdx_text)
    assert 2000 <= count <= 3000, f"Word count {count} not in [2000, 3000]"


# --- SC-02: Introduction present ---


def test_sc02_introduction_present(mdx_body: str) -> None:
    """SC-02: Introduction has 2-3 paragraphs mentioning audience, evaluation, structure."""
    intro = _get_section_between(mdx_body, "## Introduction", r"^## Stage 1")
    # Extract non-empty paragraphs (blocks of text separated by blank lines)
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", intro) if p.strip()]
    assert 2 <= len(paragraphs) <= 3, (
        f"Intro has {len(paragraphs)} paragraphs, expected 2-3"
    )
    intro_lower = intro.lower()
    assert any(
        w in intro_lower for w in ["practitioner", "trader", "portfolio", "audience"]
    ), "Introduction must mention the target audience"
    assert any(w in intro_lower for w in ["evaluation", "evaluate", "criteria"]), (
        "Introduction must mention the evaluation context"
    )
    assert any(
        w in intro_lower for w in ["cumulative", "progressive", "stage", "build"]
    ), "Introduction must mention the cumulative structure"


# --- SC-03: All six stages populated ---


def test_sc03_all_six_stages_populated(stage_sections: list[str]) -> None:
    """SC-03: Each of the six stages contains at least 2 paragraphs of explanation."""
    assert len(stage_sections) == 6, f"Expected 6 stages, found {len(stage_sections)}"
    for i, section in enumerate(stage_sections, 1):
        # Remove image refs, placeholders, details blocks, headings
        prose = re.sub(r"!\[.*?\]\(.*?\)", "", section)
        prose = re.sub(r"<Placeholder[^/]*/>\s*", "", prose)
        prose = re.sub(r"<details>.*?</details>", "", prose, flags=re.DOTALL)
        prose = re.sub(r"^## .*$", "", prose, flags=re.MULTILINE)
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", prose) if p.strip()]
        assert len(paragraphs) >= 2, (
            f"Stage {i} has {len(paragraphs)} paragraphs, expected at least 2"
        )


# --- SC-04: SVG diagram references correct ---


def test_sc04_svg_diagram_references(stage_sections: list[str]) -> None:
    """SC-04: Each stage has an image reference to the correct SVG path that exists on disk."""
    for i, (section, slug) in enumerate(zip(stage_sections, SVG_SLUGS), 1):
        expected_path = f"/img/grid-primer/{slug}.svg"
        assert expected_path in section, (
            f"Stage {i} missing image ref to {expected_path}"
        )
        fs_path = IMG_DIR / f"{slug}.svg"
        assert fs_path.exists(), f"SVG file not found: {fs_path}"


# --- SC-05: Placeholder components present ---


def test_sc05_placeholder_components(stage_sections: list[str]) -> None:
    """SC-05: Each stage has exactly one Placeholder with the correct title."""
    for i, (section, title) in enumerate(zip(stage_sections, PLACEHOLDER_TITLES), 1):
        placeholders = re.findall(r"<Placeholder\s+title=\"([^\"]+)\"\s*/>", section)
        assert len(placeholders) == 1, (
            f"Stage {i}: expected 1 Placeholder, found {len(placeholders)}"
        )
        assert placeholders[0] == title, (
            f"Stage {i}: Placeholder title mismatch: {placeholders[0]!r} != {title!r}"
        )


# --- SC-06: Placeholder import present ---


def test_sc06_placeholder_import(mdx_text: str) -> None:
    """SC-06: The MDX file imports the Placeholder component."""
    assert re.search(r"^import\s+Placeholder\s+from\s+", mdx_text, re.MULTILINE), (
        "Missing Placeholder import"
    )


# --- SC-07: KaTeX equations present ---


def test_sc07_katex_equations_present(mdx_body: str) -> None:
    """SC-07: The page contains 1-2 KaTeX equations (display math $$...$$)."""
    display_eqs = re.findall(r"\$\$.*?\$\$", mdx_body, re.DOTALL)
    assert 1 <= len(display_eqs) <= 2, (
        f"Expected 1-2 display equations, found {len(display_eqs)}"
    )


# --- SC-08: Equations in collapsible sections ---


def test_sc08_equations_in_details(mdx_body: str) -> None:
    """SC-08: Every display KaTeX equation is inside a <details> block with a <summary>."""
    # Find all details blocks
    details_blocks = re.findall(r"<details>.*?</details>", mdx_body, re.DOTALL)
    # Find all display equations
    all_eqs = re.findall(r"\$\$.*?\$\$", mdx_body, re.DOTALL)
    assert len(all_eqs) > 0, "No display equations found"
    # Every equation must be inside a details block
    for eq in all_eqs:
        in_details = any(eq in block for block in details_blocks)
        assert in_details, f"Display equation not inside <details>: {eq[:60]}..."
    # Each details block with equations must have a summary
    for block in details_blocks:
        if "$$" in block:
            assert "<summary>" in block, "Details block with equation missing <summary>"


# --- SC-09: Rubric cross-references present ---


def test_sc09_rubric_crossrefs(stage_sections: list[str]) -> None:
    """SC-09: Each stage has at least one parenthetical rubric cross-reference (A-N pattern)."""
    for i, section in enumerate(stage_sections, 1):
        assert re.search(r"A-\d+", section), (
            f"Stage {i} missing rubric cross-reference (A-N pattern)"
        )


# --- SC-10: Bridge section present ---


def test_sc10_bridge_section(mdx_body: str) -> None:
    """SC-10: A bridge section after Stage 6 links to the Expressiveness criterion page."""
    bridge_match = re.search(r"## From Primer to Evaluation", mdx_body)
    assert bridge_match, "Missing 'From Primer to Evaluation' bridge section"
    bridge_text = mdx_body[bridge_match.start() :]
    assert (
        "/docs/criteria/expressiveness" in bridge_text
        or "expressiveness" in bridge_text.lower()
    )
    # Must contain a markdown link
    assert re.search(r"\[.*?\]\(.*?expressiveness.*?\)", bridge_text), (
        "Bridge section must contain a link to the Expressiveness criterion page"
    )


# --- SC-11: Cumulative prose ---


def test_sc11_cumulative_prose(stage_sections: list[str]) -> None:
    """SC-11: Stages 2-6 reference concepts from earlier stages."""
    # Stage 2+ should reference concepts from Stage 1 (bus, power balance, generator, load)
    for i, section in enumerate(stage_sections[1:], 2):
        section_lower = section.lower()
        has_back_ref = any(
            term in section_lower
            for term in [
                "bus",
                "power balance",
                "impedance",
                "lmp",
                "opf",
                "stage",
                "earlier",
                "from stage",
                "generator",
                "congestion",
            ]
        )
        assert has_back_ref, (
            f"Stage {i} does not reference concepts from earlier stages"
        )


# --- SC-12: Valid frontmatter ---


def test_sc12_valid_frontmatter(mdx_text: str) -> None:
    """SC-12: Frontmatter has title, sidebar_position: 2, and non-empty description."""
    fm_match = re.match(r"^---\s*\n(.*?)\n---", mdx_text, re.DOTALL)
    assert fm_match, "Missing frontmatter"
    fm = fm_match.group(1)
    assert 'title: "Grid Operations Primer"' in fm
    assert "sidebar_position: 2" in fm
    desc_match = re.search(r'description:\s*"(.+?)"', fm)
    assert desc_match and len(desc_match.group(1).strip()) > 0, (
        "Frontmatter must have a non-empty description"
    )


# --- SC-13: Practitioner tone ---


def test_sc13_practitioner_tone(mdx_body: str) -> None:
    """SC-13: Technical terms are defined on first use with plain-language explanation."""
    body_lower = mdx_body.lower()
    # Key terms that should be accompanied by explanation
    terms_with_definitions = {
        "impedance": ["resistance", "reactance"],
        "lmp": ["locational marginal price", "shadow price", "cost"],
        "ptdf": ["power transfer distribution factor", "fraction", "how"],
        "scopf": ["security-constrained", "contingency"],
        "n-1": ["single element", "any single", "loss of"],
    }
    for term, explanations in terms_with_definitions.items():
        if term in body_lower:
            has_explanation = any(exp in body_lower for exp in explanations)
            assert has_explanation, (
                f"Term '{term}' used without plain-language explanation"
            )


# --- SC-14: No broken MDX syntax ---


def test_sc14_no_broken_mdx_syntax(mdx_text: str) -> None:
    """SC-14: Basic MDX syntax checks — balanced tags, valid image refs, imports."""
    # All <details> are closed
    opens = len(re.findall(r"<details>", mdx_text))
    closes = len(re.findall(r"</details>", mdx_text))
    assert opens == closes, f"Unbalanced <details> tags: {opens} opens, {closes} closes"

    # All <summary> are closed
    opens = len(re.findall(r"<summary>", mdx_text))
    closes = len(re.findall(r"</summary>", mdx_text))
    assert opens == closes, f"Unbalanced <summary> tags: {opens} opens, {closes} closes"

    # Placeholder tags are self-closing
    assert not re.search(r"</Placeholder>", mdx_text), (
        "Placeholder should be self-closing"
    )

    # Image references use valid MDX syntax
    for img in re.finditer(r"!\[.*?\]\((.*?)\)", mdx_text):
        path = img.group(1)
        assert path.startswith("/img/"), f"Image path should be absolute: {path}"


# --- SC-15: Transition sentences ---


def test_sc15_transition_sentences(stage_sections: list[str]) -> None:
    """SC-15: Stages 1-5 end with a transition; Stage 6 does not have a forward transition."""
    for i, section in enumerate(stage_sections[:5], 1):
        # Get text after the last Placeholder
        after_placeholder = section.rsplit("<Placeholder", 1)
        assert len(after_placeholder) == 2, f"Stage {i}: Could not find Placeholder"
        trailing = after_placeholder[1].split("/>", 1)
        assert len(trailing) == 2, f"Stage {i}: Malformed Placeholder"
        transition_text = trailing[1].strip()
        assert len(transition_text) > 10, (
            f"Stage {i}: Missing transition sentence after Placeholder"
        )

    # Stage 6 should NOT have significant text after Placeholder
    stage6 = stage_sections[5]
    after_ph = stage6.rsplit("<Placeholder", 1)
    if len(after_ph) == 2:
        trailing = after_ph[1].split("/>", 1)
        if len(trailing) == 2:
            remaining = trailing[1].strip()
            # Should have no substantial transition text
            assert len(remaining) < 50, (
                f"Stage 6 should not have a forward transition, found: {remaining[:80]!r}"
            )


# --- SC-16: Image alt text ---


def test_sc16_image_alt_text(mdx_body: str) -> None:
    """SC-16: Every SVG image reference includes descriptive alt text."""
    images = re.findall(r"!\[(.*?)\]\(.*?\)", mdx_body)
    assert len(images) == 6, f"Expected 6 image references, found {len(images)}"
    for i, alt in enumerate(images, 1):
        assert len(alt) >= 10, f"Image {i} has insufficient alt text: {alt!r}"


# --- SC-17: Stage headings match Deliverable 1 ---


def test_sc17_stage_headings(mdx_body: str) -> None:
    """SC-17: The six H2 headings match the Deliverable 1 specification."""
    for heading in STAGE_HEADINGS:
        assert heading in mdx_body, f"Missing expected heading: {heading}"


# --- SC-18: No orphaned concepts ---


def test_sc18_no_orphaned_concepts(mdx_body: str) -> None:
    """SC-18: Terms referenced in later stages are defined where first introduced."""
    body_lower = mdx_body.lower()

    # Map of terms to the stage section where they should first appear
    # (using heading text as anchor)
    term_first_stage = {
        "power balance": "stage 1",
        "impedance": "stage 2",
        "ptdf": "stage 3",
        "lmp": "stage 4",
        "n-1": "stage 6",
    }

    stage_positions = {}
    for n in range(1, 7):
        marker = f"## stage {n}:"
        pos = body_lower.find(marker)
        if pos >= 0:
            stage_positions[f"stage {n}"] = pos

    for term, expected_stage in term_first_stage.items():
        first_use = body_lower.find(term)
        if first_use == -1:
            continue  # Term not used at all — not an error for this test
        stage_start = stage_positions.get(expected_stage, 0)
        # Allow the term to appear at or after its expected stage start
        # (or in the introduction if it's a general term)
        intro_pos = body_lower.find("## introduction")
        assert first_use >= intro_pos, (
            f"Term '{term}' appears before the Introduction section"
        )
        # Term should not appear before its defining stage (unless in intro)
        if first_use > intro_pos + len("## introduction"):
            assert first_use >= stage_start, (
                f"Term '{term}' first used before {expected_stage}"
            )
