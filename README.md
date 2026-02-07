# Bilingual 2-Column PDF Generator

Convert a markdown document into a side-by-side bilingual PDF with the source language in the left column and its translation in the right column. Supports any language pair available through Google Translate. Defaults to French→Spanish. Corresponding paragraphs are vertically aligned.

## Quick start

```bash
# French → Spanish (default)
bilingual_pdf.py my_doc.md

# Spanish → French
bilingual_pdf.py mi_doc.md --source es --target fr

# English → German
bilingual_pdf.py my_doc.md --source en --target de
```

## How it works

1. **Parse** the input markdown into structural blocks (headings and paragraphs)
2. **Translate** each block to the target language (automatically via Google Translate, or from a pre-translated file you supply)
3. **Render** a 2-column HTML table where each row pairs a source block with its translated counterpart
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

`bilingual_pdf.py` auto-configures the Homebrew library path at runtime (`DYLD_FALLBACK_LIBRARY_PATH`), so you should not need to set it yourself.

## Usage

```bash
# French → Spanish (default)
bilingual_pdf.py document.md

# Any language pair
bilingual_pdf.py document.md --source en --target de

# Use a pre-translated markdown file
bilingual_pdf.py document.md --translation document_es.md

# Specify output filename
bilingual_pdf.py document.md -o bilingual.pdf

# Output HTML instead of PDF (useful for debugging layout/CSS)
bilingual_pdf.py document.md --html-only

# Get full help
bilingual_pdf.py --help

# French → Spanish, also save the translation markdown
bilingual_pdf.py document.md --save-translation

# List of principal supported language codes (for --source and --target)
bilingual_pdf.py --list-languages

```

**Default output filename:** `<stem>.<source>.<target>.pdf` (or `.html` with `--html-only`). If the input already ends with `.<source>.md`, the source suffix is not repeated (e.g. `doc.fr.md` → `doc.fr.es.pdf`, not `doc.fr.fr.es.pdf`).

## Input format

The input markdown should contain simple text with `#` and `##` headings:

```markdown
# Main Title

## Section

A paragraph of text. Multiple lines in the source
are joined into a single paragraph.

Another paragraph, separated by a blank line.

A web link example: [OpenAI](https://www.openai.com)
```

Supported block types: `# heading`, `## subheading`, and plain paragraphs. Blank lines separate paragraphs.

Web links are preserved and translated as part of the text.

The script does not currently support more complex markdown features (lists, tables, images, etc.) but could be extended to do so.

## Using a pre-translated file

If you prefer hand-edited translations over machine translation, provide a pre-translated markdown file with the **same structure** (same number and order of headings and paragraphs) as the source:

```bash
bilingual_pdf.py source_fr.md --translation source_es.md
```

The script warns if the block counts don't match and pads the shorter side with empty cells.

## Possible improvements

The PDF layout is controlled by a CSS block inside the `HTML_TEMPLATE` string in `bilingual_pdf.py`. Areas that could be made configurable or enhanced:

- **Page size and margins** — currently hardcoded to A4 with 2 cm margins (`@page` rule)
- **Font and size** — currently Helvetica Neue at 11 pt (`body` rule)
- **Column separator** — a thin vertical line between the two columns (`td.left` border-right)
- **Heading sizes** — `h1` at 16 pt, `h2` at 13 pt
- **Page-break behaviour** — paragraph pairs are kept together (`break-inside: avoid` on `tr`); long blocks could benefit from smarter splitting

## Example

The repository includes sample files you can use to test:

```bash
# Using auto-translation
bilingual_pdf.py sample.fr.md

# Using the provided Spanish translation
bilingual_pdf.py sample.fr.md --translation sample.es.md
```
