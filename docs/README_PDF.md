# Generating PDF Documentation

This guide explains how to generate a PDF version of the OSeMOSYS-RDM documentation.

## Prerequisites

Make sure you have the documentation dependencies installed:

```bash
pip install -r requirements.txt
```

This will install Sphinx, rinohtype, and all necessary extensions.

## Method 1: Using the Batch Script (Windows - Easiest)

Simply double-click or run from command line:

```bash
cd docs
build_pdf.bat
```

This will:
1. Install/update rinohtype
2. Build the PDF documentation
3. Open the output folder when complete

The PDF will be located at: `docs/_build/rinoh/osemosys-rdm.pdf`

## Method 2: Manual Command

From the `docs` directory, run:

```bash
sphinx-build -b rinoh . _build/rinoh
```

## Troubleshooting

### "sphinx-build not found"

Make sure you have Sphinx installed:

```bash
pip install sphinx rinohtype
```

### PDF has formatting issues

Rinohtype has some limitations with complex layouts. If you encounter issues:

1. Check that all images are in the correct format (PNG, JPEG)
2. Verify that mermaid diagrams are properly rendered
3. Consider using LaTeX builder for better quality (more complex setup)

### Missing sections in PDF

Make sure all sections are uncommented in `index.rst` if you want them in the PDF.

## Output Location

The generated PDF will be saved to:

```
docs/_build/rinoh/osemosys-rdm.pdf
```

This directory is ignored by git (see `.gitignore`).

## PDF Quality

Rinohtype provides good quality PDFs with these features:
- Table of contents with hyperlinks
- Cross-references between sections
- Syntax highlighting for code blocks
- Embedded images
- Professional layout

For production-quality PDFs with custom styling, consider using the LaTeX builder (requires LaTeX installation).