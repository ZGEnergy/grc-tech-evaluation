# Deliverables

Formal contract deliverables for Phase 1.

## Contents

| File | SOW Reference | Description |
|------|---------------|-------------|
| `whitepaper.md` | Task 1.3 | Technology evaluation white paper (markdown source) |

## Regenerating the PDF

The white paper can be converted to PDF using pandoc:

```bash
cd deliverables
pandoc whitepaper.md -o whitepaper.pdf \
  --pdf-engine=xelatex \
  -V geometry:margin=1in \
  -V fontsize=11pt
```

Requires pandoc and a LaTeX distribution (texlive-xetex).
