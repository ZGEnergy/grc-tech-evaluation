"""Tests for the link and image validation script.

Covers 18 success criteria (T-D6.01-01 through T-D6.01-18) from the PRD.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.validate_links import (
    LinkReference,
    RefType,
    build_anchor_index,
    classify_reference,
    collect_anchor_ids,
    collect_references,
    main,
    resolve_page_path,
    validate_build,
    validate_reference,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def build_dir(tmp_path: Path) -> Path:
    """Create a minimal Docusaurus-like build directory structure."""
    bd = tmp_path / "build"
    bd.mkdir()

    # index page
    (bd / "index.html").write_text(
        "<html><body>"
        '<a href="/grc-tech-evaluation/results/">Results</a>'
        '<a href="/grc-tech-evaluation/about/">About</a>'
        '<a href="#top">Top</a>'
        '<a href="https://example.com">External</a>'
        '<img src="/grc-tech-evaluation/img/logo.png">'
        "</body></html>"
    )

    # results page with anchors
    results_dir = bd / "results"
    results_dir.mkdir()
    (results_dir / "index.html").write_text(
        "<html><body>"
        '<h1 id="overview">Overview</h1>'
        '<h2 id="details">Details</h2>'
        '<a href="/grc-tech-evaluation/results/#overview">Self anchor</a>'
        '<a href="/grc-tech-evaluation/">Home</a>'
        '<a href="#details">Details link</a>'
        "</body></html>"
    )

    # about page
    about_dir = bd / "about"
    about_dir.mkdir()
    (about_dir / "index.html").write_text(
        "<html><body>"
        '<h1 id="mission">Mission</h1>'
        '<a href="/grc-tech-evaluation/results/#overview">Results overview</a>'
        '<a href="/grc-tech-evaluation/nonexistent/">Broken link</a>'
        "</body></html>"
    )

    # static asset
    img_dir = bd / "img"
    img_dir.mkdir()
    (img_dir / "logo.png").write_bytes(b"\x89PNG")

    return bd


@pytest.fixture()
def source_file(build_dir: Path) -> Path:
    """Return the index.html from the build fixture."""
    return build_dir / "index.html"


# ---------------------------------------------------------------------------
# T-D6.01-01: collect_references extracts <a href> references
# ---------------------------------------------------------------------------


def test_collect_references_extracts_a_href(tmp_path: Path) -> None:
    """collect_references should extract href from anchor tags."""
    html = tmp_path / "page.html"
    html.write_text(
        "<html><body>"
        '<a href="/grc-tech-evaluation/foo/">Link</a>'
        '<a href="#bar">Anchor</a>'
        "</body></html>"
    )
    refs = collect_references(html)
    targets = [r.target for r in refs]
    assert "/grc-tech-evaluation/foo/" in targets
    assert "#bar" in targets
    assert all(r.element_tag == "a" for r in refs)


# ---------------------------------------------------------------------------
# T-D6.01-02: collect_references extracts <img src> references
# ---------------------------------------------------------------------------


def test_collect_references_extracts_img_src(tmp_path: Path) -> None:
    """collect_references should extract src from img tags."""
    html = tmp_path / "page.html"
    html.write_text(
        '<html><body><img src="/grc-tech-evaluation/img/photo.png"></body></html>'
    )
    refs = collect_references(html)
    assert len(refs) == 1
    assert refs[0].target == "/grc-tech-evaluation/img/photo.png"
    assert refs[0].element_tag == "img"
    assert refs[0].ref_type == RefType.STATIC_ASSET


# ---------------------------------------------------------------------------
# T-D6.01-03: collect_references records line numbers
# ---------------------------------------------------------------------------


def test_collect_references_records_line_numbers(tmp_path: Path) -> None:
    """collect_references should capture the line number of each reference."""
    html = tmp_path / "page.html"
    html.write_text("<html>\n<body>\n<a href='/foo/'>Link</a>\n</body>\n</html>")
    refs = collect_references(html)
    assert len(refs) == 1
    assert refs[0].line_number == 3


# ---------------------------------------------------------------------------
# T-D6.01-04: collect_anchor_ids extracts all id attributes
# ---------------------------------------------------------------------------


def test_collect_anchor_ids(tmp_path: Path) -> None:
    """collect_anchor_ids should return all id attributes in the HTML."""
    html = tmp_path / "page.html"
    html.write_text(
        "<html><body>"
        '<h1 id="title">Title</h1>'
        '<div id="content"><p id="intro">Hello</p></div>'
        "</body></html>"
    )
    ids = collect_anchor_ids(html)
    assert ids == {"title", "content", "intro"}


# ---------------------------------------------------------------------------
# T-D6.01-05: classify_reference identifies external URLs
# ---------------------------------------------------------------------------


def test_classify_reference_external(tmp_path: Path) -> None:
    """External http/https URLs should be classified as EXTERNAL."""
    f = tmp_path / "page.html"
    f.write_text("")
    assert classify_reference("https://example.com", f) == RefType.EXTERNAL
    assert classify_reference("http://example.com/page", f) == RefType.EXTERNAL
    assert classify_reference("mailto:a@b.com", f) == RefType.EXTERNAL


# ---------------------------------------------------------------------------
# T-D6.01-06: classify_reference identifies fragment-only anchors
# ---------------------------------------------------------------------------


def test_classify_reference_fragment_only(tmp_path: Path) -> None:
    """Fragment-only hrefs should be classified as INTERNAL_ANCHOR."""
    f = tmp_path / "page.html"
    f.write_text("")
    assert classify_reference("#section", f) == RefType.INTERNAL_ANCHOR
    assert classify_reference("#top", f) == RefType.INTERNAL_ANCHOR


# ---------------------------------------------------------------------------
# T-D6.01-07: classify_reference identifies static assets
# ---------------------------------------------------------------------------


def test_classify_reference_static_asset(tmp_path: Path) -> None:
    """References to files with known asset extensions should be STATIC_ASSET."""
    f = tmp_path / "page.html"
    f.write_text("")
    assert (
        classify_reference("/grc-tech-evaluation/img/logo.png", f)
        == RefType.STATIC_ASSET
    )
    assert (
        classify_reference("/grc-tech-evaluation/assets/style.css", f)
        == RefType.STATIC_ASSET
    )
    assert classify_reference("images/photo.jpg", f) == RefType.STATIC_ASSET


# ---------------------------------------------------------------------------
# T-D6.01-08: classify_reference identifies internal page links
# ---------------------------------------------------------------------------


def test_classify_reference_internal_page(tmp_path: Path) -> None:
    """Paths without asset extensions and without fragments should be INTERNAL_PAGE."""
    f = tmp_path / "page.html"
    f.write_text("")
    assert (
        classify_reference("/grc-tech-evaluation/results/", f) == RefType.INTERNAL_PAGE
    )
    assert classify_reference("/grc-tech-evaluation/about/", f) == RefType.INTERNAL_PAGE


# ---------------------------------------------------------------------------
# T-D6.01-09: classify_reference identifies page-plus-fragment as INTERNAL_ANCHOR
# ---------------------------------------------------------------------------


def test_classify_reference_page_plus_fragment(tmp_path: Path) -> None:
    """Page + fragment hrefs should be classified as INTERNAL_ANCHOR."""
    f = tmp_path / "page.html"
    f.write_text("")
    ref_type = classify_reference("/grc-tech-evaluation/results/#overview", f)
    assert ref_type == RefType.INTERNAL_ANCHOR


# ---------------------------------------------------------------------------
# T-D6.01-10: resolve_page_path handles trailing slash -> index.html
# ---------------------------------------------------------------------------


def test_resolve_page_path_trailing_slash(build_dir: Path) -> None:
    """A trailing-slash path should resolve to the directory's index.html."""
    source = build_dir / "index.html"
    resolved = resolve_page_path("/grc-tech-evaluation/results/", source, build_dir)
    assert resolved is not None
    assert resolved.name == "index.html"
    assert "results" in str(resolved)


# ---------------------------------------------------------------------------
# T-D6.01-11: resolve_page_path handles root path
# ---------------------------------------------------------------------------


def test_resolve_page_path_root(build_dir: Path) -> None:
    """The base URL root should resolve to build_dir/index.html."""
    source = build_dir / "results" / "index.html"
    resolved = resolve_page_path("/grc-tech-evaluation/", source, build_dir)
    assert resolved is not None
    assert resolved == (build_dir / "index.html").resolve()


# ---------------------------------------------------------------------------
# T-D6.01-12: resolve_page_path returns None for missing pages
# ---------------------------------------------------------------------------


def test_resolve_page_path_missing(build_dir: Path) -> None:
    """A path to a non-existent page should return None."""
    source = build_dir / "index.html"
    resolved = resolve_page_path("/grc-tech-evaluation/nonexistent/", source, build_dir)
    assert resolved is None


# ---------------------------------------------------------------------------
# T-D6.01-13: validate_reference passes valid internal page link
# ---------------------------------------------------------------------------


def test_validate_reference_valid_page(build_dir: Path) -> None:
    """A valid internal page link should pass validation."""
    anchor_index = build_anchor_index(build_dir)
    ref = LinkReference(
        source_file=build_dir / "index.html",
        target="/grc-tech-evaluation/results/",
        ref_type=RefType.INTERNAL_PAGE,
        element_tag="a",
        line_number=1,
    )
    result = validate_reference(ref, build_dir, anchor_index)
    assert result.is_valid is True


# ---------------------------------------------------------------------------
# T-D6.01-14: validate_reference fails broken internal page link
# ---------------------------------------------------------------------------


def test_validate_reference_broken_page(build_dir: Path) -> None:
    """A broken internal page link should fail validation."""
    anchor_index = build_anchor_index(build_dir)
    ref = LinkReference(
        source_file=build_dir / "about" / "index.html",
        target="/grc-tech-evaluation/nonexistent/",
        ref_type=RefType.INTERNAL_PAGE,
        element_tag="a",
        line_number=1,
    )
    result = validate_reference(ref, build_dir, anchor_index)
    assert result.is_valid is False
    assert result.error_message is not None


# ---------------------------------------------------------------------------
# T-D6.01-15: validate_reference validates anchors within same page
# ---------------------------------------------------------------------------


def test_validate_reference_same_page_anchor(build_dir: Path) -> None:
    """A fragment-only anchor should be validated against the same file's ids."""
    anchor_index = build_anchor_index(build_dir)
    ref_good = LinkReference(
        source_file=build_dir / "results" / "index.html",
        target="#details",
        ref_type=RefType.INTERNAL_ANCHOR,
        element_tag="a",
        line_number=1,
    )
    ref_bad = LinkReference(
        source_file=build_dir / "results" / "index.html",
        target="#nonexistent",
        ref_type=RefType.INTERNAL_ANCHOR,
        element_tag="a",
        line_number=2,
    )
    assert validate_reference(ref_good, build_dir, anchor_index).is_valid is True
    assert validate_reference(ref_bad, build_dir, anchor_index).is_valid is False


# ---------------------------------------------------------------------------
# T-D6.01-16: validate_reference validates cross-page anchors
# ---------------------------------------------------------------------------


def test_validate_reference_cross_page_anchor(build_dir: Path) -> None:
    """A page+fragment reference should verify the anchor in the target page."""
    anchor_index = build_anchor_index(build_dir)
    ref_good = LinkReference(
        source_file=build_dir / "about" / "index.html",
        target="/grc-tech-evaluation/results/#overview",
        ref_type=RefType.INTERNAL_ANCHOR,
        element_tag="a",
        line_number=1,
    )
    ref_bad = LinkReference(
        source_file=build_dir / "about" / "index.html",
        target="/grc-tech-evaluation/results/#missing_anchor",
        ref_type=RefType.INTERNAL_ANCHOR,
        element_tag="a",
        line_number=2,
    )
    assert validate_reference(ref_good, build_dir, anchor_index).is_valid is True
    assert validate_reference(ref_bad, build_dir, anchor_index).is_valid is False


# ---------------------------------------------------------------------------
# T-D6.01-17: validate_build produces correct report with external count
# ---------------------------------------------------------------------------


def test_validate_build_report(build_dir: Path) -> None:
    """validate_build should count externals and detect the broken link."""
    report = validate_build(build_dir)

    assert report.total_references > 0
    assert report.external_skipped >= 1  # at least the https://example.com link
    assert report.internal_checked > 0
    # The about page has a broken link to /nonexistent/
    assert len(report.broken) >= 1
    broken_targets = [r.reference.target for r in report.broken]
    assert any("nonexistent" in t for t in broken_targets)
    assert report.passed is False


# ---------------------------------------------------------------------------
# T-D6.01-18: CLI exit codes
# ---------------------------------------------------------------------------


def test_cli_exit_code_missing_dir(tmp_path: Path) -> None:
    """CLI should exit 2 when the build directory does not exist."""
    missing = tmp_path / "no_such_dir"
    code = main([str(missing)])
    assert code == 2


def test_cli_exit_code_no_html(tmp_path: Path) -> None:
    """CLI should exit 2 when the build directory has no HTML files."""
    empty_dir = tmp_path / "empty_build"
    empty_dir.mkdir()
    code = main([str(empty_dir)])
    assert code == 2


def test_cli_exit_code_clean_build(tmp_path: Path) -> None:
    """CLI should exit 0 for a build with all valid internal links."""
    bd = tmp_path / "clean_build"
    bd.mkdir()
    (bd / "index.html").write_text(
        '<html><body><h1 id="top">Home</h1><a href="#top">Top</a></body></html>'
    )
    code = main([str(bd), "--base-url", "/grc-tech-evaluation/"])
    assert code == 0


def test_cli_exit_code_broken_build(build_dir: Path) -> None:
    """CLI should exit 1 when broken links are present."""
    code = main([str(build_dir), "--base-url", "/grc-tech-evaluation/"])
    assert code == 1
