#!/bin/bash
# General/portable setup — no conda, no machine-specific paths. Works on the
# recommended host (Streamlit Community Cloud) and any generic Linux
# environment with python3 available. For this dev machine's conda setup,
# use setup_PC.sh instead.
set -e
cd "$(dirname "$0")"

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
