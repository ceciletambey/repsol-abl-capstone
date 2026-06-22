#!/usr/bin/env bash
# One-command environment setup. Run from the project root:
#     bash setup.sh
set -e

echo "→ Creating virtual environment..."
python -m venv .venv

echo "→ Activating and installing dependencies..."
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo "→ Preparing .env..."
if [ ! -f .env ]; then
  cp .env.example .env
  echo "  Created .env — now paste your real GOOGLE_API_KEY into it."
else
  echo "  .env already exists, leaving it untouched."
fi

echo ""
echo "Done. Next steps:"
echo "  1. Edit .env and paste your Gemini key (https://aistudio.google.com)"
echo "  2. source .venv/bin/activate"
echo "  3. python smoke_test.py        # should print: ABL pipeline online"
echo "  4. python -m graph.build_graph # runs the full pipeline"
