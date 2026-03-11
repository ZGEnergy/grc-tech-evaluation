.PHONY: charts charts-validate build serve clean validate validate-dev smoke

# Python chart generation (Phase 1: skeleton only)
charts:
	uv run python scripts/generate_charts.py

# Validate chart manifest and file integrity (independent of generation)
charts-validate:
	uv run python scripts/validate_charts.py

# Full build: generate charts, then compile Docusaurus site
build: charts
	npm run build

# Start Docusaurus dev server for local preview
serve:
	npm run start

# Post-build validation (strict — CI mode)
validate: build
	@echo "=== Running link & image validation ==="
	uv run python scripts/validate_links.py build
	@echo "=== Running chart-manifest cross-reference validation ==="
	uv run python scripts/validate_chart_manifest.py
	@echo "=== Running content validation (strict) ==="
	uv run python scripts/validate_content.py build --config docusaurus.config.js
	@echo "=== All validations passed ==="

# Post-build validation (permissive — local dev mode)
validate-dev: build
	@echo "=== Running link & image validation ==="
	uv run python scripts/validate_links.py build
	@echo "=== Running chart-manifest cross-reference validation ==="
	uv run python scripts/validate_chart_manifest.py
	@echo "=== Running content validation (permissive) ==="
	uv run python scripts/validate_content.py build --allow-placeholders --config docusaurus.config.js
	@echo "=== All validations passed ==="

# Post-deployment smoke test (requires live site)
smoke:
	@echo "=== Running deployment smoke test ==="
	uv run python scripts/smoke_test.py
	@echo "=== Smoke test passed ==="

# Remove all build artifacts
clean:
	rm -rf build .docusaurus
	rm -rf static/img/generated
	rm -f static/img/chart-manifest.json
