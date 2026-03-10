.PHONY: charts build serve clean

# Python chart generation (Phase 1: skeleton only)
charts:
	uv run python scripts/generate_charts.py

# Full build: generate charts, then compile Docusaurus site
build: charts
	npm run build

# Start Docusaurus dev server for local preview
serve:
	npm run start

# Remove all build artifacts
clean:
	rm -rf build .docusaurus
	rm -rf static/img/generated
	rm -f static/img/chart-manifest.json
