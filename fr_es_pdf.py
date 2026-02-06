#!/usr/bin/env python3
"""
Convert a markdown document to a 2-column bilingual (FR/ES) PDF.

Usage:
    python fr_es_pdf.py sample.md                        # FR→ES (default)
    python fr_es_pdf.py sample.md --direction es-fr      # ES→FR
    python fr_es_pdf.py sample.md --translation es.md    # use pre-translated file
    python fr_es_pdf.py sample.md --stub                 # use stub (for dev)
    python fr_es_pdf.py sample.md -o output.pdf          # specify output filename
    python fr_es_pdf.py sample.md --html-only            # write HTML for debugging

Prerequisites:
    pip install weasyprint deep-translator markdown

Note (macOS / Homebrew):
    If weasyprint fails to find gobject/pango, run with:
        DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python fr_es_pdf.py ...
"""

import argparse
import os
import platform
import re
import sys

# macOS / Homebrew: help weasyprint find native libs and silence GLib warnings
if platform.system() == "Darwin":
    _brew_lib = "/opt/homebrew/lib"
    if os.path.isdir(_brew_lib):
        os.environ.setdefault("DYLD_FALLBACK_LIBRARY_PATH", _brew_lib)
    os.environ.setdefault("G_DEBUG", "fatal-criticals=0")
    os.environ.setdefault("GLIB_LOG_LEVEL", "0")

# ---------------------------------------------------------------------------
# Step 1: Parse markdown into blocks
# ---------------------------------------------------------------------------


def parse_markdown(text):
    """Parse markdown text into a list of blocks.

    Each block is a dict with:
        type: 'h1', 'h2', or 'p'
        text: the raw text content (no markdown markers)
    """
    blocks = []
    current_paragraph_lines = []

    def flush_paragraph():
        if current_paragraph_lines:
            blocks.append({
                "type": "p",
                "text": " ".join(current_paragraph_lines),
            })
            current_paragraph_lines.clear()

    for line in text.splitlines():
        stripped = line.strip()

        # blank line → flush any accumulated paragraph
        if not stripped:
            flush_paragraph()
            continue

        # headings
        m = re.match(r'^(#{1,2})\s+(.*)', stripped)
        if m:
            flush_paragraph()
            level = len(m.group(1))
            blocks.append({
                "type": f"h{level}",
                "text": m.group(2).strip(),
            })
            continue

        # otherwise it's a paragraph line
        current_paragraph_lines.append(stripped)

    flush_paragraph()
    return blocks


# ---------------------------------------------------------------------------
# Step 2: Translate blocks
# ---------------------------------------------------------------------------

def translate_stub(blocks, target_lang="es"):
    """Return blocks with stub translations (for development)."""
    label = target_lang.upper()
    translated = []
    for b in blocks:
        translated.append({**b, "text": f"[{label}] {b['text']}"})
    return translated


def translate_with_google(blocks, source="fr", target="es"):
    """Translate blocks using deep-translator (Google Translate)."""
    from deep_translator import GoogleTranslator

    translator = GoogleTranslator(source=source, target=target)
    translated = []
    for b in blocks:
        translated_text = translator.translate(b["text"])
        translated.append({**b, "text": translated_text})
    return translated


def load_translated_file(path):
    """Load a pre-translated markdown file and parse it into blocks."""
    with open(path, encoding="utf-8") as f:
        return parse_markdown(f.read())


# ---------------------------------------------------------------------------
# Step 3: Generate 2-column HTML
# ---------------------------------------------------------------------------

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<style>
  @page {{
    size: A4;
    margin: 2cm;
  }}
  body {{
    font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.4;
    color: #222;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
  }}
  td {{
    vertical-align: top;
    padding: 4pt 8pt;
    width: 50%;
  }}
  /* thin vertical separator */
  td.left {{
    border-right: 0.5pt solid #ccc;
    padding-right: 12pt;
  }}
  td.right {{
    padding-left: 12pt;
  }}
  tr {{
    break-inside: avoid;
  }}
  h1, h2 {{
    margin: 0;
  }}
  td h1 {{
    font-size: 16pt;
    margin-top: 12pt;
    margin-bottom: 2pt;
  }}
  td h2 {{
    font-size: 13pt;
    margin-top: 10pt;
    margin-bottom: 2pt;
  }}
  td p {{
    margin: 4pt 0;
  }}
  /* column headers */
  thead th {{
    font-size: 9pt;
    text-transform: uppercase;
    letter-spacing: 1pt;
    color: #888;
    border-bottom: 1pt solid #ccc;
    padding-bottom: 4pt;
    text-align: left;
  }}
</style>
</head>
<body>
<table>
  <thead>
    <tr><th>{left_label}</th><th>{right_label}</th></tr>
  </thead>
  <tbody>
{rows}
  </tbody>
</table>
</body>
</html>
"""


def _html_cell(block):
    """Render a single block as an HTML fragment."""
    tag = block["type"] if block["type"] in ("h1", "h2") else "p"
    return f"<{tag}>{block['text']}</{tag}>"


def generate_html(left_blocks, right_blocks, left_label="Fran\u00e7ais", right_label="Espa\u00f1ol"):
    """Build a full HTML document with a 2-column table."""
    if len(left_blocks) != len(right_blocks):
        print(
            f"Warning: block count mismatch (left={len(left_blocks)}, right={len(right_blocks)}). "
            "Padding shorter side with empty cells.",
            file=sys.stderr,
        )

    rows_html = []
    n = max(len(left_blocks), len(right_blocks))
    for i in range(n):
        left_cell = _html_cell(left_blocks[i]) if i < len(left_blocks) else ""
        right_cell = _html_cell(right_blocks[i]) if i < len(right_blocks) else ""
        rows_html.append(
            f'    <tr><td class="left">{left_cell}</td><td class="right">{right_cell}</td></tr>'
        )

    return HTML_TEMPLATE.format(
        rows="\n".join(rows_html),
        left_label=left_label,
        right_label=right_label,
    )


# ---------------------------------------------------------------------------
# Step 4: Convert HTML → PDF
# ---------------------------------------------------------------------------

def _mute_stderr():
    """Redirect C-level stderr to /dev/null (silences GLib warnings).

    Does NOT restore stderr — GLib also emits warnings at process exit,
    so we keep it muted for the lifetime of the process.
    """
    devnull = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull, sys.stderr.fileno())
    os.close(devnull)


def html_to_pdf(html_string, output_path):
    """Write HTML to PDF using weasyprint."""
    _mute_stderr()
    from weasyprint import HTML
    HTML(string=html_string).write_pdf(output_path)
    # Use stdout — stderr is permanently muted after weasyprint
    print(f"PDF written to: {output_path}")


# ---------------------------------------------------------------------------
# Step 5: CLI
# ---------------------------------------------------------------------------

LANG_LABELS = {"fr": "Fran\u00e7ais", "es": "Espa\u00f1ol"}


def main():
    parser = argparse.ArgumentParser(
        description="Convert markdown to a 2-column bilingual FR/ES PDF."
    )
    parser.add_argument("input", help="Path to the source markdown file")
    parser.add_argument(
        "-o", "--output", default=None,
        help="Output PDF path (default: <input>.pdf)",
    )
    parser.add_argument(
        "--direction", choices=["fr-es", "es-fr"], default="fr-es",
        help="Translation direction (default: fr-es)",
    )
    parser.add_argument(
        "--translation",
        help="Path to a pre-translated markdown file",
    )
    parser.add_argument(
        "--stub", action="store_true",
        help="Use stub translations (for development/testing)",
    )
    parser.add_argument(
        "--html-only", action="store_true",
        help="Write intermediate HTML instead of PDF (for debugging layout)",
    )

    args = parser.parse_args()

    source_lang, target_lang = args.direction.split("-")

    # -- read & parse source --
    with open(args.input, encoding="utf-8") as f:
        source_blocks = parse_markdown(f.read())

    # -- translate --
    if args.translation:
        target_blocks = load_translated_file(args.translation)
    elif args.stub:
        target_blocks = translate_stub(source_blocks, target_lang=target_lang)
    else:
        target_blocks = translate_with_google(source_blocks, source=source_lang, target=target_lang)

    # -- generate HTML --
    html = generate_html(
        source_blocks,
        target_blocks,
        left_label=LANG_LABELS[source_lang],
        right_label=LANG_LABELS[target_lang],
    )

    # -- output --
    if args.output:
        out_path = args.output
    else:
        out_path = re.sub(r"\.md$", "", args.input) + (
            ".html" if args.html_only else ".pdf"
        )

    if args.html_only:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"HTML written to: {out_path}")
    else:
        html_to_pdf(html, out_path)


if __name__ == "__main__":
    main()
