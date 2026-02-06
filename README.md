# French-Spanish 2-Column PDF Generator

Convert a French markdown document into a side-by-side bilingual PDF with the French original in the left column and its Spanish translation in the right column. Corresponding paragraphs are vertically aligned.

## Quick start

Create a markdown document with some text in French, then run:

```bash
fr_es_pdf.py my_doc.md
```

This will generate `my_doc.pdf` with the French text in the left column and the Spanish translation in the right column.

## How it works

1. **Parse** the input markdown into structural blocks (headings and paragraphs)
2. **Translate** each block to Spanish (automatically via Google Translate, or from a pre-translated file you supply)
3. **Render** a 2-column HTML table where each row pairs a French block with its Spanish counterpart
4. **Convert** the HTML to an A4 PDF using WeasyPrint

## Installation

The quickest way to install all dependencies is with the provided script:

```bash
bash install_deps.sh
```

This will:

- Install the Python packages (`weasyprint`, `deep-translator`) into whichever `python3` is on your PATH
- On macOS, check that `pango` is available via Homebrew (and install it if missing)
- Verify that WeasyPrint can load its native libraries

If you use conda or virtualenv, activate the target environment first:

```bash
conda activate myenv
bash install_deps.sh
```

### Manual installation

If you prefer to install manually:

```bash
pip install weasyprint deep-translator
brew install pango          # macOS only
```

The script auto-configures the Homebrew library path at runtime (`DYLD_FALLBACK_LIBRARY_PATH`), so you should not need to set it yourself.

## Usage

```bash
# Auto-translate with Google Translate (no API key needed)
fr_es_pdf.py document.md

# Use a pre-translated Spanish markdown file
fr_es_pdf.py document.md --translation document_es.md

# Specify output filename
fr_es_pdf.py document.md -o bilingual.pdf

# Output HTML instead of PDF (useful for debugging layout/CSS)
fr_es_pdf.py document.md --html-only

# Stub translation — prefixes each block with [ES] (for development)
fr_es_pdf.py document.md --stub
```

**Default output filename:** `<input>.pdf` (or `<input>.html` with `--html-only`), replacing the `.md` extension.

## Input format

The input markdown should contain simple text with `#` and `##` headings:

```markdown
# Main Title

## Section

A paragraph of French text. Multiple lines in the source
are joined into a single paragraph.

Another paragraph, separated by a blank line.
```

Supported block types: `# heading`, `## subheading`, and plain paragraphs. Blank lines separate paragraphs.

## Using a pre-translated file

If you prefer hand-edited translations over machine translation, provide a Spanish markdown file with the **same structure** (same number and order of headings and paragraphs) as the French source:

```bash
fr_es_pdf.py source_fr.md --translation source_es.md
```

The script warns if the block counts don't match and pads the shorter side with empty cells.

## Customizing the layout

The PDF styling is controlled by a CSS block inside the `HTML_TEMPLATE` string in `fr_es_pdf.py`. You can adjust:

- **Page size and margins:** the `@page` rule (default: A4 with 2cm margins)
- **Font and size:** the `body` rule (default: Helvetica Neue, 11pt)
- **Column separator:** the `td.fr` border-right property
- **Heading sizes:** the `td h1` / `td h2` rules
- **Page breaks:** `break-inside: avoid` on `tr` prevents a paragraph pair from being split across pages

## Example

The repository includes sample files you can use to test:

```bash
# Using auto-translation
fr_es_pdf.py sample.md

# Using the provided Spanish translation
fr_es_pdf.py sample.md --translation sample_es.md
```
