#!/bin/bash
cd /app
uv run python process.py &
uv run streamlit run app.py --server.port=8504 --server.address=0.0.0.0