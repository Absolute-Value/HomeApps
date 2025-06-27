#!/bin/bash
uv run python process.py &
uv run streamlit run app.py --server.port=8504 --server.enableCORS=false --server.enableXsrfProtection=false --server.headless=true
