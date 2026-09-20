#!/bin/bash
# General/portable start — no conda, no machine-specific paths. Binds to
# $PORT when the host provides one (as most cloud platforms do), otherwise
# defaults to Streamlit's standard port. For this dev machine's conda setup,
# use start_PC.sh instead.
set -e
cd "$(dirname "$0")"

source .venv/bin/activate
streamlit run app.py --server.port="${PORT:-8501}" --server.address=0.0.0.0
