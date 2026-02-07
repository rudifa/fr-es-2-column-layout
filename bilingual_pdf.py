#!/usr/bin/env python3
"""
Convert a markdown document to a 2-column bilingual PDF.

Usage:
    python bilingual_pdf.py sample.md                          # FR→ES (default)
    python bilingual_pdf.py sample.md --source es --target fr  # ES→FR
    python bilingual_pdf.py sample.md --source en --target de  # EN→DE
    python bilingual_pdf.py sample.md --translation es.md      # use pre-translated file
    python bilingual_pdf.py sample.md -o output.pdf            # specify output filename
    # default output: sample.fr.es.pdf
    python bilingual_pdf.py sample.md --html-only              # write HTML for debugging

Prerequisites:
    pip install weasyprint deep-translator markdown

Note (macOS / Homebrew):
    If weasyprint fails to find gobject/pango, run with:
        DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python bilingual_pdf.py ...
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

def _validate_lang_codes(source, target):
    """Check that source and target language codes are supported by Google Translate."""
    from deep_translator import GoogleTranslator

    supported = GoogleTranslator().get_supported_languages(as_dict=True)
    # supported is {name: code}, build a set of valid codes
    valid_codes = set(supported.values())

    bad = []
    if source not in valid_codes:
        bad.append(source)
    if target not in valid_codes:
        bad.append(target)

    if bad:
        print(
            f"Error: unsupported language code(s): {', '.join(bad)}", file=sys.stderr)
        print(f"\nSupported languages:", file=sys.stderr)
        for name, code in sorted(supported.items()):
            print(f"  {code:<6} {name}", file=sys.stderr)
        sys.exit(1)


def translate_with_google(blocks, source="fr", target="es"):
    """Translate blocks using deep-translator (Google Translate)."""
    from deep_translator import GoogleTranslator

    translator = GoogleTranslator(source=source, target=target)
    translated = []
    for b in blocks:
        translated_text = translator.translate(b["text"])
        translated.append({**b, "text": translated_text})
    return translated


def blocks_to_markdown(blocks):
    """Convert a list of blocks back to markdown text."""
    lines = []
    for b in blocks:
        if b["type"] == "h1":
            lines.append(f"# {b['text']}")
        elif b["type"] == "h2":
            lines.append(f"## {b['text']}")
        else:
            lines.append(b["text"])
        lines.append("")
    return "\n".join(lines)


def load_translated_file(path):
    """Load a pre-translated markdown file and parse it into blocks."""
    with open(path, encoding="utf-8") as f:
        return parse_markdown(f.read())


# ---------------------------------------------------------------------------
# Step 3: Generate 2-column HTML
# ---------------------------------------------------------------------------

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="{source_lang}">
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


def _inline_markdown(text):
    """Convert inline markdown markers to HTML (bold, italic, links)."""
    # [text](url)  →  <a href="url">text</a>  (processed first to protect link text from bold/italic)
    text = re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)',
                  r'<a href="\2">\1</a>', text)
    # ***bold italic***  →  <strong><em>…</em></strong>
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', text)
    # **bold** or __bold__  →  <strong>
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'__(.+?)__', r'<strong>\1</strong>', text)
    # *italic* or _italic_  →  <em>
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    text = re.sub(r'(?<!\w)_(.+?)_(?!\w)', r'<em>\1</em>', text)
    return text


def _html_cell(block):
    """Render a single block as an HTML fragment."""
    tag = block["type"] if block["type"] in ("h1", "h2") else "p"
    return f"<{tag}>{_inline_markdown(block['text'])}</{tag}>"


def generate_html(left_blocks, right_blocks, left_label, right_label, source_lang="fr"):
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
        right_cell = _html_cell(right_blocks[i]) if i < len(
            right_blocks) else ""
        rows_html.append(
            f'    <tr><td class="left">{left_cell}</td><td class="right">{right_cell}</td></tr>'
        )

    return HTML_TEMPLATE.format(
        rows="\n".join(rows_html),
        left_label=left_label,
        right_label=right_label,
        source_lang=source_lang,
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

# Endonyms for common languages; unknown codes fall back to uppercase code.
LANG_LABELS = {
    "ar": "\u0627\u0644\u0639\u0631\u0628\u064a\u0629",
    "de": "Deutsch",
    "en": "English",
    "es": "Espa\u00f1ol",
    "fr": "Fran\u00e7ais",
    "hr": "Hrvatski",
    "it": "Italiano",
    "ja": "\u65e5\u672c\u8a9e",
    "ko": "\ud55c\uad6d\uc5b4",
    "nl": "Nederlands",
    "pl": "Polski",
    "pt": "Portugu\u00eas",
    "ro": "Rom\u00e2n\u0103",
    "ru": "\u0420\u0443\u0441\u0441\u043a\u0438\u0439",
    "uk": "\u0423\u043a\u0440\u0430\u0457\u043d\u0441\u044c\u043a\u0430",
    "zh-CN": "\u4e2d\u6587",
}


def lang_label(code):
    """Return a display label for a language code (endonym or uppercase code)."""
    return LANG_LABELS.get(code, code.upper())


def main():
    parser = argparse.ArgumentParser(
        description="Convert source markdown text to a 2-column bilingual PDF.",
    )
    parser.add_argument("input", nargs="?",
                        help="(required) path to the source markdown file")
    parser.add_argument(
        "--list-languages", action="store_true",
        help="list available languages with endonyms and exit",
    )
    parser.add_argument(
        "-o", "--output", default=None,
        help="output PDF path (default: <input>.<source>.<target>.pdf)",
    )
    parser.add_argument(
        "--source", default="fr",
        help="source language code (default: fr)",
    )
    parser.add_argument(
        "--target", default="es",
        help="target language code (default: es)",
    )
    parser.add_argument(
        "--translation",
        help="path to a pre-translated markdown file (default: use google translate)",
    )
    parser.add_argument(
        "--save-translation", action="store_true",
        help="save the translated text as <input>.<target>.md (ignored with --translation)",
    )
    parser.add_argument(
        "--html-only", action="store_true",
        help="write intermediate HTML instead of PDF (for debugging layout)",
    )

    args = parser.parse_args()

    # -- list languages and exit --
    if args.list_languages:
        for code, label in sorted(LANG_LABELS.items()):
            print(f"  {code:<6} {label}")
        print(
            f"\nOther codes (e.g. 'sv', 'fi') known to Google Translate can also be used.")
        sys.exit(0)

    # -- validate input file --
    if not args.input:
        parser.error("the following argument is required: input")
    if not args.input.endswith(".md"):
        parser.error(f"input file must have .md extension: {args.input}")
    if not os.path.isfile(args.input):
        parser.error(f"input file not found: {args.input}")

    # -- validate output file --
    if args.output:
        expected_ext = ".html" if args.html_only else ".pdf"
        if not args.output.endswith(expected_ext):
            parser.error(
                f"output file must have {expected_ext} extension: {args.output}")

    source_lang = args.source
    target_lang = args.target
    left_label = lang_label(source_lang)
    right_label = lang_label(target_lang)

    # Compute base stem: strip .md, then strip .<source> suffix if present
    # e.g. "sample.fr.md" with --source fr → stem "sample"
    #      "sample.md"    with --source fr → stem "sample"
    stem = re.sub(r"\.md$", "", args.input)
    if stem.endswith(f".{source_lang}"):
        stem = stem[: -len(f".{source_lang}")]

    # -- read & parse source --
    with open(args.input, encoding="utf-8") as f:
        source_blocks = parse_markdown(f.read())

    # -- translate --
    if args.translation:
        target_blocks = load_translated_file(args.translation)
    else:
        _validate_lang_codes(source_lang, target_lang)
        target_blocks = translate_with_google(
            source_blocks, source=source_lang, target=target_lang)

    # -- save translation if requested --
    if args.save_translation and not args.translation:
        trans_path = f"{stem}.{target_lang}.md"
        with open(trans_path, "w", encoding="utf-8") as f:
            f.write(blocks_to_markdown(target_blocks))
        print(f"Translation written to: {trans_path}")

    # -- generate HTML --
    html = generate_html(
        source_blocks,
        target_blocks,
        left_label=left_label,
        right_label=right_label,
        source_lang=source_lang,
    )

    # -- output --
    if args.output:
        out_path = args.output
    else:
        out_path = (
            f"{stem}.{source_lang}.{target_lang}.html" if args.html_only
            else f"{stem}.{source_lang}.{target_lang}.pdf"
        )

    if args.html_only:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"HTML written to: {out_path}")
    else:
        html_to_pdf(html, out_path)


if __name__ == "__main__":
    main()
