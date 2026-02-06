#!/bin/bash
# Install dependencies for fr_es_pdf.py into the active Python environment.
#
# Usage:
#   bash install_deps.sh          # install into whatever python3 is on PATH
#   conda activate myenv && bash install_deps.sh   # install into a specific env

set -e

PYTHON="$(which python3)"
echo "Installing into: $PYTHON"
echo "  ($(python3 --version))"
echo

# Python packages
python3 -m pip install --quiet weasyprint deep-translator
echo "Python packages installed."

# Check for system libraries needed by weasyprint (macOS)
if [[ "$(uname)" == "Darwin" ]]; then
    if ! brew list pango &>/dev/null 2>&1; then
        echo
        echo "weasyprint needs pango. Installing via Homebrew..."
        brew install pango
    fi

    # Verify weasyprint can load its native libraries
    if ! DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 -c "from weasyprint import HTML" 2>/dev/null; then
        echo
        echo "WARNING: weasyprint cannot load native libraries."
        echo "You may need to run commands with:"
        echo "  DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 fr_es_pdf.py ..."
    else
        echo "weasyprint native libraries OK."
    fi
fi

echo
echo "Done. Verify with:"
echo "  python3 -c \"from deep_translator import GoogleTranslator; print('deep-translator OK')\""
echo "  DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 -c \"from weasyprint import HTML; print('weasyprint OK')\""
